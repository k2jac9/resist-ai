"""Stage 2b: novel drug candidate generation via MolMIM."""
from __future__ import annotations

import logging

from ..models.schemas import ScreeningHit, TargetResult
from .clients import get_nim
from .demo_data import DEMO_SEQUENCES

logger = logging.getLogger(__name__)


class NovelMoleculeGenerator:
    """Stage 2b: Generate novel drug candidates via MolMIM."""

    def generate_from_hits(
        self,
        top_hits: list[ScreeningHit],
        target: TargetResult,
        molecules_per_hit: int = 3,
        max_hits: int = 3,
    ) -> list[dict]:
        """Generate novel molecules from top screening hits."""
        from .stages import stage_generate_molecules, stage_screen_drug

        nim = get_nim()
        if not nim or not nim.available:
            logger.info("NIM unavailable; skipping novel molecule generation")
            return []

        target_seq = DEMO_SEQUENCES.get(target.name, "")
        all_novels: list[dict] = []

        for hit in top_hits[:max_hits]:
            gen = stage_generate_molecules(
                nim, seed_smiles=hit.smiles,
                num_molecules=molecules_per_hit,
                property_name="QED", min_similarity=0.3,
            )
            if gen["success"]:
                for mol in gen["molecules"]:
                    smiles = mol["smiles"]
                    qed = mol["score"]

                    binding_conf = 0.0
                    if target_seq and smiles:
                        binding = stage_screen_drug(nim, target_seq, smiles)
                        if binding["success"]:
                            binding_conf = binding["confidence"]

                    all_novels.append({
                        "smiles": smiles,
                        "qed_score": round(qed, 4),
                        "seed_drug": hit.drug_name,
                        "binding_confidence": round(binding_conf, 4),
                        "target": target.name,
                        "source": "MolMIM (NVIDIA NIM)",
                    })

                logger.info(
                    "MolMIM generated %d novel molecules from %s",
                    gen["num_generated"], hit.drug_name,
                )

        return all_novels
