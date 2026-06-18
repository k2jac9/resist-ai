"""ResistAI Pipeline SDK -- composable, chainable drug-discovery pipeline.

Wraps the existing NIMClient and NebisLLM into a lazy-execution pipeline
that queues steps and runs them in order when ``.run()`` is called.

Usage::

    from src.sdk import Pipeline, Target

    target = Target.from_sequence("MELPNIMH...", name="NDM-1")
    results = (
        Pipeline(target)
        .fold()
        .screen(drugs=[{"name": "Meropenem", "smiles": "CC(...)O"}])
        .dock(top_k=3)
        .generate(n=5, optimize="QED")
        .validate()
        .design_binder()
        .analyze()
        .run(progress=True)
    )
    print(results.to_report())
"""
from __future__ import annotations

import logging
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from src.sdk.results import (
    BinderDesign,
    DockingPose,
    NovelMolecule,
    PipelineResults,
    ScreeningHit,
    ValidationResult,
)
from src.sdk.target import Target

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Step descriptors (internal)
# ---------------------------------------------------------------------------

@dataclass
class _Step:
    """A single queued pipeline step."""

    name: str
    fn: Callable[[PipelineResults], None]
    kwargs: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Default drug library (fallback when no drugs list supplied)
# ---------------------------------------------------------------------------

_DEFAULT_DRUGS: list[dict[str, str]] = [
    {"name": "Meropenem", "smiles": "CC(C1C2CC(=C(N2C1=O)C(=O)O)SC3CC(NC3)C(=O)N(C)C)O"},
    {"name": "Ciprofloxacin", "smiles": "C1CC1N2C=C(C(=O)C3=CC(=C(C=C32)N4CCNCC4)F)C(=O)O"},
    {"name": "Amoxicillin", "smiles": "CC1(C(N2C(S1)C(C2=O)NC(=O)C(C3=CC=C(C=C3)O)N)C(=O)O)C"},
    {"name": "Linezolid", "smiles": "CC(=O)NCC1CN(C(=O)O1)C2=CC(=C(C=C2)N3CCOCC3)F"},
    {"name": "Doxycycline", "smiles": "CC1C2C(C3C(C(=O)C(=C(C3(C(=O)C2=C(C4=C1C=CC=C4O)O)O)O)C(=O)N)N(C)C)O"},
]


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class Pipeline:
    """Lazy, chainable drug-discovery pipeline backed by NVIDIA NIM.

    Steps are recorded when their methods are called but only executed
    when ``.run()`` is invoked, in the order they were added.

    Args:
        target: The protein target to run the pipeline against.
    """

    def __init__(self, target: Target) -> None:
        self._target = target
        self._steps: list[_Step] = []
        self._nim: Any = None  # lazy NIMClient
        self._llm: Any = None  # lazy NebisLLM

    # ------------------------------------------------------------------
    # Lazy client accessors
    # ------------------------------------------------------------------

    def _get_nim(self) -> Any:
        """Return (or create) the NIMClient singleton for this pipeline."""
        if self._nim is None:
            from src.models.nim_client import NIMClient
            self._nim = NIMClient()
        return self._nim

    def _get_llm(self) -> Any:
        """Return (or create) the NebisLLM singleton for this pipeline."""
        if self._llm is None:
            from src.models.llm_client import NebisLLM
            self._llm = NebisLLM()
        return self._llm

    # ------------------------------------------------------------------
    # Step builders (each returns self for chaining)
    # ------------------------------------------------------------------

    def fold(self) -> Pipeline:
        """Queue ESMFold structure prediction for the target sequence."""

        def _run_fold(results: PipelineResults) -> None:
            from src.pipeline.stages import stage_fold_protein

            nim = self._get_nim()
            fold = stage_fold_protein(nim, self._target.sequence)
            if fold["success"]:
                results.structure = fold["pdb_string"]
                results.structure_length = len(fold["pdb_string"])
                results.fold_elapsed_ms = fold["elapsed_ms"]
                self._target.pdb_string = fold["pdb_string"]
            elif not nim or not nim.available:
                results.errors.append({"step": "fold", "error": "NIM client unavailable (no API key)"})
            else:
                results.errors.append({"step": "fold", "error": "ESMFold returned no structure"})

        self._steps.append(_Step(name="fold", fn=_run_fold))
        return self

    def screen(
        self,
        drugs: Optional[list[dict[str, str]]] = None,
    ) -> Pipeline:
        """Queue Boltz-2 binding screening against a drug library.

        Args:
            drugs: List of dicts with ``name`` and ``smiles`` keys.
                   Falls back to a built-in antibiotic library when omitted.
        """
        drug_list = drugs if drugs is not None else _DEFAULT_DRUGS

        def _run_screen(results: PipelineResults) -> None:
            from src.pipeline.stages import stage_screen_drug

            nim = self._get_nim()
            if not nim or not nim.available:
                results.errors.append({"step": "screen", "error": "NIM client unavailable"})
                return
            for drug in drug_list:
                name = drug.get("name", "unknown")
                smiles = drug.get("smiles", "")
                if not smiles:
                    continue
                binding = stage_screen_drug(nim, self._target.sequence, smiles)
                if binding["success"]:
                    results.screening_hits.append(ScreeningHit(
                        drug_name=name,
                        smiles=smiles,
                        confidence=binding["confidence"],
                        ptm_score=binding["ptm_score"],
                        iptm_score=binding["iptm_score"],
                        ligand_iptm=binding["ligand_iptm"],
                        structure_cif=binding["structure_cif"],
                        raw=binding["raw"],
                    ))
                else:
                    results.errors.append({"step": "screen", "drug": name, "error": "Boltz-2 binding failed"})
            # Sort by confidence descending
            results.screening_hits.sort(key=lambda h: h.confidence, reverse=True)

        self._steps.append(_Step(name="screen", fn=_run_screen))
        return self

    def dock(self, top_k: int = 5, num_poses: int = 5) -> Pipeline:
        """Queue DiffDock 3D docking for the top screening hits.

        Requires a PDB structure (from ``fold()`` or the target itself).

        Args:
            top_k:     Number of top screening hits to dock.
            num_poses: Number of poses per ligand.
        """

        def _run_dock(results: PipelineResults) -> None:
            from src.pipeline.stages import stage_dock as _stage_dock

            nim = self._get_nim()
            if not nim or not nim.available:
                results.errors.append({"step": "dock", "error": "NIM client unavailable"})
                return
            pdb = self._target.pdb_string or (results.structure or "")
            if not pdb or len(pdb) < 100:
                results.errors.append({
                    "step": "dock",
                    "error": "No PDB structure available; run fold() first or use Target.from_pdb()",
                })
                return
            # Pick candidates from screening hits, or use default drugs
            candidates: list[dict[str, str]] = []
            if results.screening_hits:
                for hit in results.screening_hits[:top_k]:
                    candidates.append({"name": hit.drug_name, "smiles": hit.smiles})
            else:
                candidates = _DEFAULT_DRUGS[:top_k]

            for drug in candidates:
                name = drug.get("name", "unknown")
                smiles = drug.get("smiles", "")
                if not smiles:
                    continue
                dock = _stage_dock(nim, pdb, smiles, num_poses=num_poses)
                if dock["success"]:
                    for i, pos in enumerate(dock["ligand_positions"]):
                        conf = (
                            dock["position_confidence"][i]
                            if i < len(dock["position_confidence"])
                            else 0.0
                        )
                        results.docking_poses.append(DockingPose(
                            ligand_sdf=pos,
                            confidence=conf,
                            drug_name=name,
                            smiles=smiles,
                        ))
                else:
                    results.errors.append({"step": "dock", "drug": name, "error": "DiffDock docking failed"})
            # Sort by confidence descending
            results.docking_poses.sort(key=lambda p: p.confidence, reverse=True)

        self._steps.append(_Step(name="dock", fn=_run_dock))
        return self

    def generate(
        self,
        n: int = 10,
        optimize: str = "QED",
        seed_smiles: Optional[str] = None,
        min_similarity: float = 0.3,
    ) -> Pipeline:
        """Queue MolMIM novel molecule generation.

        Args:
            n:              Number of molecules to generate.
            optimize:       Property to optimize (``"QED"``, ``"logP"``, etc.).
            seed_smiles:    Starting SMILES. Defaults to top screening hit.
            min_similarity: Minimum Tanimoto similarity to seed.
        """

        def _run_generate(results: PipelineResults) -> None:
            from src.pipeline.stages import stage_generate_molecules

            nim = self._get_nim()
            if not nim or not nim.available:
                results.errors.append({"step": "generate", "error": "NIM client unavailable"})
                return
            seed = seed_smiles
            if not seed:
                if results.screening_hits:
                    seed = results.screening_hits[0].smiles
                else:
                    seed = _DEFAULT_DRUGS[0]["smiles"]
            gen = stage_generate_molecules(
                nim, seed_smiles=seed, num_molecules=n,
                property_name=optimize, min_similarity=min_similarity,
            )
            if gen["success"]:
                for mol in gen["molecules"]:
                    results.novel_molecules.append(NovelMolecule(
                        smiles=mol["smiles"],
                        score=float(mol["score"]),
                        score_type=gen["score_type"],
                        seed_smiles=seed,
                    ))
            else:
                results.errors.append({"step": "generate", "error": "MolMIM returned no molecules"})

        self._steps.append(_Step(name="generate", fn=_run_generate))
        return self

    def validate(self) -> Pipeline:
        """Queue Boltz-2 binding validation for generated novel molecules."""

        def _run_validate(results: PipelineResults) -> None:
            from src.pipeline.stages import stage_screen_drug

            nim = self._get_nim()
            if not nim or not nim.available:
                results.errors.append({"step": "validate", "error": "NIM client unavailable"})
                return
            mols = results.novel_molecules
            if not mols:
                results.errors.append({"step": "validate", "error": "No novel molecules to validate"})
                return
            for mol in mols:
                if not mol.smiles:
                    continue
                binding = stage_screen_drug(nim, self._target.sequence, mol.smiles)
                if binding["success"]:
                    results.validated_molecules.append(ValidationResult(
                        smiles=mol.smiles,
                        confidence=binding["confidence"],
                        iptm_score=binding["iptm_score"],
                        success=True,
                    ))
                else:
                    results.errors.append({"step": "validate", "smiles": mol.smiles[:40], "error": "Boltz-2 validation failed"})
            results.validated_molecules.sort(key=lambda v: v.confidence, reverse=True)

        self._steps.append(_Step(name="validate", fn=_run_validate))
        return self

    def design_binder(self, contigs: str = "10-40/A1-60/10-40") -> Pipeline:
        """Queue RFdiffusion backbone design + ProteinMPNN sequence design.

        Requires a PDB structure on the target.

        Args:
            contigs: RFdiffusion contig specification.
        """

        def _run_design(results: PipelineResults) -> None:
            from src.pipeline.stages import stage_design_binder

            nim = self._get_nim()
            if not nim or not nim.available:
                results.errors.append({"step": "design_binder", "error": "NIM client unavailable"})
                return
            pdb = self._target.pdb_string or (results.structure or "")
            if not pdb or len(pdb) < 100:
                results.errors.append({
                    "step": "design_binder",
                    "error": "No PDB structure; run fold() first",
                })
                return
            binder = stage_design_binder(nim, pdb, contigs=contigs)
            if binder["success"]:
                results.binder_design = BinderDesign(
                    backbone_pdb=binder["backbone_pdb"],
                    sequences=binder["sequences"],
                    success=True,
                )
            else:
                results.errors.append({"step": "design_binder", "error": "RFdiffusion/ProteinMPNN failed"})
                results.binder_design = BinderDesign(success=False)

        self._steps.append(_Step(name="design_binder", fn=_run_design))
        return self

    def analyze(self, prompt: Optional[str] = None) -> Pipeline:
        """Queue LLM-powered analysis of all pipeline results so far.

        Args:
            prompt: Custom prompt override. By default a comprehensive
                    summary prompt is generated from the results.
        """

        def _run_analyze(results: PipelineResults) -> None:
            llm = self._get_llm()
            if not llm.available:
                results.errors.append({"step": "analyze", "error": "LLM client unavailable"})
                return
            if prompt:
                text = llm.complete(prompt)
            else:
                text = self._auto_analyze(results, llm)
            results.analysis = text or None

        self._steps.append(_Step(name="analyze", fn=_run_analyze))
        return self

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def run(self, progress: bool = False) -> PipelineResults:
        """Execute all queued steps in order and return results.

        Args:
            progress: If ``True``, print step names and timing to stderr.
        """
        results = PipelineResults(
            target_name=self._target.name,
            target_sequence=self._target.sequence,
            started_at=datetime.now(timezone.utc).isoformat(),
        )

        for step in self._steps:
            if progress:
                print(f"  [{step.name}] running...", end="", file=sys.stderr, flush=True)
            t0 = time.time()
            try:
                step.fn(results)
            except Exception as exc:
                results.errors.append({"step": step.name, "error": str(exc)})
                logger.error("Step %s failed: %s", step.name, exc)
            elapsed = time.time() - t0
            results.steps_executed.append(step.name)
            if progress:
                print(f" done ({elapsed:.1f}s)", file=sys.stderr, flush=True)

        results.finished_at = datetime.now(timezone.utc).isoformat()
        return results

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _auto_analyze(self, results: PipelineResults, llm: Any) -> str:
        """Build and run a comprehensive analysis prompt from results."""
        parts: list[str] = [
            f"Analyze these drug-discovery pipeline results for target '{self._target.name}'",
            f"(sequence length: {self._target.length} aa, source: {self._target.source}).",
            "",
        ]
        if results.structure is not None:
            parts.append(f"- Structure predicted via ESMFold ({results.structure_length} chars)")
        if results.screening_hits:
            top = results.screening_hits[:5]
            hits_str = ", ".join(
                f"{h.drug_name} (conf={h.confidence:.3f})" for h in top
            )
            parts.append(f"- Screening: {len(results.screening_hits)} drugs tested, top hits: {hits_str}")
        if results.docking_poses:
            parts.append(f"- Docking: {len(results.docking_poses)} poses generated")
        if results.novel_molecules:
            parts.append(f"- MolMIM generated {len(results.novel_molecules)} novel molecules")
        if results.validated_molecules:
            top_v = results.validated_molecules[:3]
            v_str = ", ".join(f"conf={v.confidence:.3f}" for v in top_v)
            parts.append(f"- Validation: {len(results.validated_molecules)} molecules validated, top: {v_str}")
        if results.binder_design:
            parts.append(f"- Binder design success: {results.binder_design.success}")
        parts.append("")
        parts.append(
            "Provide: (1) key findings, (2) most promising candidates and why, "
            "(3) recommended next experimental steps, (4) limitations of this computational analysis."
        )
        full_prompt = "\n".join(parts)
        system = (
            "You are an expert computational biologist interpreting an AI-driven "
            "antimicrobial drug discovery pipeline. Be concise and actionable."
        )
        return llm.complete(full_prompt, system=system, max_tokens=1500)

    def __repr__(self) -> str:
        step_names = [s.name for s in self._steps]
        return f"Pipeline(target={self._target.name!r}, steps={step_names})"
