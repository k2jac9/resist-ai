"""MolMIM-powered novel molecule generation for AMR drug candidates.

Uses NVIDIA NIM MolMIM to generate optimized novel molecules from
seed compounds (screening hits), then validates them back through
Boltz-2 for binding confirmation.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from src.models.nim_client import NIMClient, Boltz2Result, MolMIMResult
from src.utils.chemistry import (
    compute_descriptors,
    passes_lipinski,
    tanimoto_similarity,
    validate_smiles,
)

logger = logging.getLogger(__name__)


@dataclass
class NovelCandidate:
    """A novel AI-generated drug candidate."""

    smiles: str
    qed_score: float = 0.0
    seed_smiles: str = ""
    seed_drug_name: str = ""
    similarity_to_seed: float = 0.0
    passes_lipinski: bool = False
    binding_confidence: float = 0.0
    binding_iptm: float = 0.0
    binding_plddt: float = 0.0
    descriptors: dict = field(default_factory=dict)
    validated: bool = False


@dataclass
class GenerationResults:
    """Results from a molecule generation + validation run."""

    seed_drug: str = ""
    seed_smiles: str = ""
    target_name: str = ""
    candidates: list[NovelCandidate] = field(default_factory=list)
    total_generated: int = 0
    total_valid: int = 0
    total_validated_binding: int = 0


class MolMIMGenerator:
    """Generates and validates novel drug candidates using MolMIM + Boltz-2."""

    def __init__(self, nim_client: Optional[NIMClient] = None) -> None:
        self._nim = nim_client or NIMClient()

    def generate_from_hit(
        self,
        seed_smiles: str,
        seed_drug_name: str = "Unknown",
        target_sequence: str = "",
        target_name: str = "",
        num_molecules: int = 5,
        property_name: str = "QED",
        min_similarity: float = 0.3,
        validate_binding: bool = True,
    ) -> GenerationResults:
        """Generate novel molecules from a screening hit and validate.

        Pipeline:
        1. MolMIM generates optimized variants of the seed
        2. Filter by Lipinski and SMILES validity
        3. (Optional) Boltz-2 validates binding to target protein

        Args:
            seed_smiles: SMILES of the seed hit compound.
            seed_drug_name: Name of the seed drug.
            target_sequence: Protein sequence for binding validation.
            target_name: Human-readable target name.
            num_molecules: Number of molecules to generate.
            property_name: Property to optimize (QED, logP, etc.).
            min_similarity: Minimum similarity to seed.
            validate_binding: Whether to run Boltz-2 binding validation.

        Returns:
            GenerationResults with validated novel candidates.
        """
        results = GenerationResults(
            seed_drug=seed_drug_name,
            seed_smiles=seed_smiles,
            target_name=target_name,
        )

        if not self._nim.available:
            logger.warning("NIM client unavailable; skipping molecule generation")
            return results

        # Step 1: Generate with MolMIM
        logger.info(
            "Generating %d novel molecules from %s (opt=%s, min_sim=%.2f)",
            num_molecules, seed_drug_name, property_name, min_similarity,
        )
        gen_result: MolMIMResult = self._nim.generate_molecules(
            seed_smiles=seed_smiles,
            num_molecules=num_molecules,
            property_name=property_name,
            min_similarity=min_similarity,
        )

        if not gen_result.success:
            logger.warning("MolMIM generation failed for %s", seed_drug_name)
            return results

        results.total_generated = gen_result.num_generated

        # Step 2: Filter and characterize
        candidates: list[NovelCandidate] = []
        for mol_data in gen_result.molecules:
            smiles = mol_data.get("sample", "")
            score = mol_data.get("score", 0.0)

            if not smiles or not validate_smiles(smiles):
                continue

            # Compute descriptors
            desc = compute_descriptors(smiles) or {}
            lipinski = passes_lipinski(smiles)

            # Similarity to seed
            sim = tanimoto_similarity(seed_smiles, smiles)
            if sim is None:
                sim = 0.0

            candidate = NovelCandidate(
                smiles=smiles,
                qed_score=round(score, 4),
                seed_smiles=seed_smiles,
                seed_drug_name=seed_drug_name,
                similarity_to_seed=round(sim, 4),
                passes_lipinski=lipinski,
                descriptors=desc,
            )
            candidates.append(candidate)

        results.total_valid = len(candidates)
        logger.info(
            "Generated %d molecules, %d valid (Lipinski pass: %d)",
            results.total_generated,
            results.total_valid,
            sum(1 for c in candidates if c.passes_lipinski),
        )

        # Step 3: Validate binding with Boltz-2
        if validate_binding and target_sequence and candidates:
            validated = 0
            for candidate in candidates:
                if not candidate.passes_lipinski:
                    continue
                try:
                    binding: Boltz2Result = self._nim.predict_binding(
                        protein_sequence=target_sequence,
                        ligand_smiles=candidate.smiles,
                    )
                    if binding.success:
                        candidate.binding_confidence = round(binding.confidence_score, 4)
                        candidate.binding_iptm = round(binding.iptm_score, 4)
                        candidate.binding_plddt = round(binding.complex_plddt, 4)
                        candidate.validated = True
                        validated += 1
                        logger.info(
                            "  Novel mol validated: conf=%.3f iptm=%.3f plddt=%.3f",
                            binding.confidence_score,
                            binding.iptm_score,
                            binding.complex_plddt,
                        )
                except Exception as exc:
                    logger.warning("Boltz-2 validation failed for novel mol: %s", exc)

            results.total_validated_binding = validated

        # Sort by QED score, validated first
        candidates.sort(
            key=lambda c: (c.validated, c.qed_score), reverse=True
        )
        results.candidates = candidates
        return results

    def generate_from_top_hits(
        self,
        hits: list[dict],
        target_sequence: str = "",
        target_name: str = "",
        molecules_per_hit: int = 3,
        max_hits: int = 3,
        validate_binding: bool = True,
    ) -> list[GenerationResults]:
        """Generate novel molecules from multiple screening hits.

        Args:
            hits: List of dicts with 'smiles', 'name' keys.
            target_sequence: Protein sequence for validation.
            target_name: Human-readable target name.
            molecules_per_hit: Molecules to generate per hit.
            max_hits: Maximum hits to use as seeds.
            validate_binding: Whether to run Boltz-2 validation.

        Returns:
            List of GenerationResults, one per seed hit.
        """
        all_results: list[GenerationResults] = []
        for hit in hits[:max_hits]:
            smiles = hit.get("smiles", "")
            name = hit.get("name", hit.get("drug_name", "Unknown"))
            if not smiles:
                continue

            result = self.generate_from_hit(
                seed_smiles=smiles,
                seed_drug_name=name,
                target_sequence=target_sequence,
                target_name=target_name,
                num_molecules=molecules_per_hit,
                validate_binding=validate_binding,
            )
            all_results.append(result)

        return all_results
