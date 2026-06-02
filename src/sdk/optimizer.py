"""Closed-loop molecule optimization engine.

Runs Generate -> Dock -> Score -> Mutate -> Repeat using NVIDIA NIM
(MolMIM for generation, Boltz-2 for binding) and RDKit for drug-likeness.

Usage::

    from resistai.optimizer import MoleculeOptimizer

    optimizer = MoleculeOptimizer(
        target_sequence="MELPNIMH...",
        seed_smiles="OB(O)C1CCC(CC(=O)NC2CCNC2)CC1",
        objectives=["binding", "qed", "lipinski", "toxicity"],
        max_iterations=5,
        molecules_per_iteration=5,
    )
    results = optimizer.run()
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from src.models.nim_client import NIMClient
from src.utils.chemistry import (
    compute_descriptors,
    passes_lipinski,
    tanimoto_similarity,
    validate_smiles,
)

logger = logging.getLogger(__name__)

VALID_OBJECTIVES = frozenset({"binding", "qed", "lipinski", "toxicity"})


@dataclass
class Candidate:
    """A molecule candidate with multi-objective scores and lineage."""

    smiles: str
    scores: Dict[str, float] = field(default_factory=dict)
    parent_smiles: Optional[str] = None
    generation: int = 0
    raw_molmim: Optional[dict] = None

    def dominates(self, other: "Candidate", objectives: Sequence[str]) -> bool:
        """True if self >= other on all objectives and strictly > on at least one."""
        better_count = 0
        for obj in objectives:
            s, o = self.scores.get(obj, 0.0), other.scores.get(obj, 0.0)
            if s < o:
                return False
            if s > o:
                better_count += 1
        return better_count > 0

    def weighted_score(self, weights: Dict[str, float]) -> float:
        return sum(self.scores.get(k, 0.0) * w for k, w in weights.items())

    def __repr__(self) -> str:
        sc = ", ".join(f"{k}={v:.3f}" for k, v in self.scores.items())
        return f"Candidate({self.smiles!r}, gen={self.generation}, {sc})"


@dataclass
class OptimizationResult:
    """Aggregate output of the optimisation loop."""

    all_candidates: List[Candidate] = field(default_factory=list)
    pareto_frontier: List[Candidate] = field(default_factory=list)
    best_per_objective: Dict[str, Candidate] = field(default_factory=dict)
    history: List[dict] = field(default_factory=list)
    iterations_run: int = 0

    def summary(self) -> str:
        lines = [
            f"Optimization complete: {self.iterations_run} iterations, "
            f"{len(self.all_candidates)} total candidates",
            f"Pareto frontier size: {len(self.pareto_frontier)}",
        ]
        for obj, cand in self.best_per_objective.items():
            lines.append(f"  Best {obj}: {cand.scores.get(obj, 0):.4f}  ({cand.smiles})")
        return "\n".join(lines)


# -- Scoring helpers ----------------------------------------------------------

def _score_toxicity(smiles: str) -> float:
    """Heuristic toxicity score [0,1] -- higher means less toxic (better)."""
    desc = compute_descriptors(smiles)
    if desc is None:
        return 0.0
    penalty = 0.0
    mw = desc["MW"]
    if mw > 500:
        penalty += min((mw - 500) / 500, 0.4)
    elif mw < 150:
        penalty += 0.2
    logp = desc["LogP"]
    if logp > 5:
        penalty += min((logp - 5) / 5, 0.3)
    elif logp < -1:
        penalty += 0.1
    if desc["TPSA"] > 140:
        penalty += 0.15
    if desc["RotBonds"] > 10:
        penalty += 0.1
    return max(0.0, 1.0 - penalty)


def _extract_qed(mol_dict: dict) -> float:
    """Extract QED from a MolMIM molecule dict."""
    for key in ("qed", "score"):
        if key in mol_dict:
            return float(mol_dict[key])
    return 0.0


def compute_pareto_frontier(
    candidates: List[Candidate], objectives: Sequence[str],
) -> List[Candidate]:
    """Return candidates not dominated by any other candidate."""
    frontier: List[Candidate] = []
    for cand in candidates:
        if not any(
            other.dominates(cand, objectives)
            for other in candidates
            if other is not cand
        ):
            frontier.append(cand)
    return frontier


# -- Main optimiser -----------------------------------------------------------

class MoleculeOptimizer:
    """Closed-loop multi-objective molecule optimiser.

    Args:
        target_sequence: Amino-acid sequence of the protein target.
        seed_smiles: Starting SMILES (e.g. Taniborbactam).
        objectives: Objectives to maximise (binding, qed, lipinski, toxicity).
        max_iterations: Generate-score-select rounds.
        molecules_per_iteration: Variants per seed per round.
        weights: Objective -> weight mapping for scalar ranking.
        min_similarity: Min Tanimoto similarity for MolMIM generation.
        top_k: Seeds carried forward each iteration.
        nim_client: Pre-configured NIMClient (auto-created if omitted).
    """

    def __init__(
        self,
        target_sequence: str,
        seed_smiles: str,
        objectives: Optional[List[str]] = None,
        max_iterations: int = 5,
        molecules_per_iteration: int = 5,
        weights: Optional[Dict[str, float]] = None,
        min_similarity: float = 0.3,
        top_k: int = 3,
        nim_client: Optional[NIMClient] = None,
    ) -> None:
        if not target_sequence:
            raise ValueError("target_sequence must be a non-empty protein sequence")
        if not validate_smiles(seed_smiles):
            raise ValueError(f"seed_smiles is not a valid SMILES: {seed_smiles!r}")

        self.target_sequence = target_sequence
        self.seed_smiles = seed_smiles
        self.objectives = list(objectives or ["binding", "qed", "lipinski", "toxicity"])
        for obj in self.objectives:
            if obj not in VALID_OBJECTIVES:
                raise ValueError(f"Unknown objective {obj!r}; valid: {sorted(VALID_OBJECTIVES)}")

        self.max_iterations = max_iterations
        self.molecules_per_iteration = molecules_per_iteration
        self.min_similarity = min_similarity
        self.top_k = top_k
        self.nim = nim_client or NIMClient()

        if weights is not None:
            self.weights = weights
        else:
            w = 1.0 / len(self.objectives)
            self.weights = {obj: w for obj in self.objectives}

    def _generate_variants(self, seed: str) -> List[dict]:
        """Call MolMIM to generate variants from a seed SMILES."""
        result = self.nim.generate_molecules(
            seed_smiles=seed,
            num_molecules=self.molecules_per_iteration,
            property_name="QED",
            min_similarity=self.min_similarity,
        )
        if not result.success:
            logger.warning("MolMIM generation failed for seed %s", seed)
            return []
        return result.molecules

    def _score_binding(self, smiles: str) -> float:
        """Score binding affinity via Boltz-2 confidence (0-1)."""
        result = self.nim.predict_binding(
            protein_sequence=self.target_sequence,
            ligand_smiles=smiles,
        )
        if not result.success:
            logger.debug("Boltz-2 failed for %s", smiles)
            return 0.0
        return result.confidence_score

    def _score_candidate(self, smiles: str, mol_dict: dict) -> Dict[str, float]:
        """Compute all requested objective scores for a molecule."""
        scores: Dict[str, float] = {}
        if "binding" in self.objectives:
            scores["binding"] = self._score_binding(smiles)
        if "qed" in self.objectives:
            scores["qed"] = _extract_qed(mol_dict)
        if "lipinski" in self.objectives:
            scores["lipinski"] = 1.0 if passes_lipinski(smiles) else 0.0
        if "toxicity" in self.objectives:
            scores["toxicity"] = _score_toxicity(smiles)
        return scores

    def _select_seeds(self, candidates: List[Candidate]) -> List[str]:
        """Pick top-k unique candidates by weighted score as next seeds."""
        ranked = sorted(candidates, key=lambda c: c.weighted_score(self.weights), reverse=True)
        seen: set[str] = set()
        seeds: List[str] = []
        for cand in ranked:
            if cand.smiles not in seen:
                seen.add(cand.smiles)
                seeds.append(cand.smiles)
            if len(seeds) >= self.top_k:
                break
        return seeds

    def _best_weighted(self, candidates: List[Candidate]) -> float:
        if not candidates:
            return -math.inf
        return max(c.weighted_score(self.weights) for c in candidates)

    def run(self) -> OptimizationResult:
        """Execute the full closed-loop optimisation.

        Returns an OptimizationResult with all candidates, the Pareto
        frontier, best-per-objective, and per-iteration history.
        """
        all_candidates: List[Candidate] = []
        history: List[dict] = []
        seeds = [self.seed_smiles]
        no_improve_count = 0
        prev_best = -math.inf

        for iteration in range(1, self.max_iterations + 1):
            logger.info("=== Iteration %d/%d | seeds: %d ===", iteration, self.max_iterations, len(seeds))
            iter_candidates: List[Candidate] = []
            all_smiles = {c.smiles for c in all_candidates}

            for seed in seeds:
                for mol_dict in self._generate_variants(seed):
                    # MolMIM returns the generated SMILES under "sample";
                    # fall back to other keys for non-NIM sources.
                    smiles = mol_dict.get("sample", mol_dict.get("smiles", mol_dict.get("smi", "")))
                    if not smiles or not validate_smiles(smiles):
                        continue
                    if smiles in all_smiles or any(c.smiles == smiles for c in iter_candidates):
                        continue

                    scores = self._score_candidate(smiles, mol_dict)
                    iter_candidates.append(Candidate(
                        smiles=smiles, scores=scores,
                        parent_smiles=seed, generation=iteration,
                        raw_molmim=mol_dict,
                    ))

            all_candidates.extend(iter_candidates)
            iter_best = self._best_weighted(iter_candidates) if iter_candidates else 0.0
            history.append({
                "iteration": iteration,
                "seeds": list(seeds),
                "num_generated": len(iter_candidates),
                "best_weighted_score": iter_best,
                "candidates": [{"smiles": c.smiles, "scores": dict(c.scores)} for c in iter_candidates],
            })
            logger.info("  Generated %d candidates | best weighted=%.4f", len(iter_candidates), iter_best)

            # Early stopping: no improvement for 2 consecutive iterations
            if iter_best <= prev_best:
                no_improve_count += 1
                if no_improve_count >= 2:
                    logger.info("Early stopping: no improvement for %d iterations", no_improve_count)
                    break
            else:
                no_improve_count = 0
                prev_best = iter_best

            seeds = self._select_seeds(all_candidates)
            if not seeds:
                logger.warning("No viable seeds; stopping early")
                break

        # Build final result
        pareto = compute_pareto_frontier(all_candidates, self.objectives)
        best_per_obj: Dict[str, Candidate] = {}
        for obj in self.objectives:
            if all_candidates:
                best_per_obj[obj] = max(all_candidates, key=lambda c, o=obj: c.scores.get(o, 0.0))

        result = OptimizationResult(
            all_candidates=all_candidates, pareto_frontier=pareto,
            best_per_objective=best_per_obj, history=history,
            iterations_run=len(history),
        )
        logger.info(result.summary())
        return result
