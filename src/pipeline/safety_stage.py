"""Stage 3: per-drug ADMET and off-target safety scoring."""
from __future__ import annotations

import logging

from ..models.schemas import (
    ADMETResult,
    OffTarget,
    OffTargetReport,
    SafetyReport,
    ScreeningHit,
)

logger = logging.getLogger(__name__)


class SafetyScorer:
    """Stage 3: ADMET + off-target safety assessment for a screening hit."""

    def score_drug(self, hit: ScreeningHit) -> SafetyReport:
        """Produce a safety report for a screening hit."""
        from .stages import stage_safety_score

        data = stage_safety_score(hit.drug_name)
        admet_d = data["admet"]
        admet = ADMETResult(
            drug_name=hit.drug_name,
            absorption=admet_d["absorption"],
            distribution=admet_d["distribution"],
            metabolism=admet_d["metabolism"],
            excretion=admet_d["excretion"],
            toxicity_score=admet_d["toxicity_score"],
            oral_bioavailability=admet_d["oral_bioavailability"],
            bbb_penetration=admet_d["bbb_penetration"],
            herg_liability=admet_d["herg_liability"],
        )
        off_targets = [
            OffTarget(
                protein_name=ot["protein_name"],
                similarity=ot["similarity"],
                risk_level=ot["risk_level"],
                tissue=ot["tissue"],
            )
            for ot in data["off_targets"]
        ]
        return SafetyReport(
            drug_name=hit.drug_name,
            smiles=hit.smiles,
            safety_score=data["safety_score"],
            admet=admet,
            off_target_report=OffTargetReport(
                drug_name=hit.drug_name,
                off_targets=off_targets,
                overall_risk="high" if data["high_risk"] else "low",
            ),
            flags=data["flags"],
            recommendation=data["recommendation"],
        )
