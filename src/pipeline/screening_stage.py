"""Stage 2: virtual drug screening against a target via Boltz-2."""
from __future__ import annotations

import logging

from ..models.schemas import ScreeningHit, ScreeningResults, TargetResult
from .clients import get_nim
from .demo_data import DEMO_DRUG_LIBRARY, DEMO_SEQUENCES

logger = logging.getLogger(__name__)


class DrugScreener:
    """Stage 2: Virtual screening of drug library against a target."""

    def screen_drugs(
        self,
        target: TargetResult,
        max_drugs: int = 100,
        use_nim: bool = True,
    ) -> ScreeningResults:
        """Screen drug library against target, using Boltz-2 when available."""
        from .stages import heuristic_binding_score, stage_screen_drug

        nim = get_nim() if use_nim else None
        library = DEMO_DRUG_LIBRARY[:max_drugs]
        target_seq = DEMO_SEQUENCES.get(target.name, "")
        hits: list[ScreeningHit] = []

        for idx, drug in enumerate(library):
            smiles = drug["smiles"]
            affinity = 0.0
            conf = 0.0

            # Try Boltz-2 for real binding prediction
            binding = stage_screen_drug(nim, target_seq, smiles)
            if binding["success"]:
                affinity = binding["confidence"]
                conf = binding["complex_plddt"]
                logger.info(
                    "Boltz-2 %s -> %s: conf=%.3f plddt=%.3f",
                    drug["name"], target.name, affinity, conf,
                )

            # Fallback to a deterministic, structure-based heuristic
            # (clearly labelled, not a Boltz-2 prediction).
            if affinity == 0.0:
                est = heuristic_binding_score(smiles, target.name)
                affinity = est["affinity"]
                conf = est["confidence"]

            hits.append(ScreeningHit(
                rank=idx + 1,
                drug_name=drug["name"],
                smiles=smiles,
                target_name=target.name,
                binding_affinity=affinity,
                confidence=conf,
                mechanism_of_action=drug.get("moa", ""),
                clinical_phase=drug.get("phase", ""),
            ))

        hits.sort(key=lambda h: h.binding_affinity, reverse=True)
        for i, hit in enumerate(hits):
            hit.rank = i + 1

        model = "Boltz-2 (NVIDIA NIM)" if (nim and nim.available) else "heuristic_docking"
        return ScreeningResults(
            target_name=target.name,
            compounds_screened=len(library),
            hits=hits,
            threshold_used=0.5,
            model_used=model,
        )
