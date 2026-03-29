"""Combined safety scoring that merges ADMET and off-target analyses."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from .admet_predictor import ADMETPredictor, ADMETResult
from .off_target_analyzer import OffTargetAnalyzer, OffTargetReport

logger = logging.getLogger(__name__)

# Pre-computed demo data for common antibiotics (SMILES sourced from PubChem).
DEMO_DRUGS: dict[str, dict] = {
    "ciprofloxacin": {
        "smiles": "O=C(O)c1cn(C2CC2)c2cc(N3CCNCC3)c(F)cc2c1=O",
        "name": "Ciprofloxacin",
    },
    "amoxicillin": {
        "smiles": "CC1(C)SC2C(NC(=O)C(N)c3ccc(O)cc3)C(=O)N2C1C(=O)O",
        "name": "Amoxicillin",
    },
    "doxycycline": {
        "smiles": "OC1C2CC3C(=C(O)c4c(O)cccc4C3(C)O)C(=O)C2(O)CC1N(C)C",
        "name": "Doxycycline",
    },
    "azithromycin": {
        "smiles": "CCC1OC(=O)C(C)C(OC2CC(C)(OC)C(O)C(C)O2)C(C)C(OC2OC(C)CC(N(C)C)C2O)C(C)(O)CC(C)CN(C)C1C",
        "name": "Azithromycin",
    },
    "trimethoprim": {
        "smiles": "COc1cc(Cc2cnc(N)nc2N)cc(OC)c1OC",
        "name": "Trimethoprim",
    },
}


@dataclass
class SafetyReport:
    """Complete safety assessment for a drug candidate."""

    drug_name: str
    smiles: str
    admet: ADMETResult | None = None
    off_targets: OffTargetReport | None = None
    overall_score: float = 0.0
    risk_level: str = "unknown"
    regulatory_flags: list[str] = field(default_factory=list)
    recommendation: str = ""


def _generate_regulatory_flags(
    admet: ADMETResult, off_target: OffTargetReport
) -> list[str]:
    """Identify regulatory red flags from ADMET and off-target data."""
    flags: list[str] = []

    tox = admet.toxicity
    if tox.get("herg_inhibition", 0) > 0.4:
        flags.append("hERG liability detected (cardiac risk)")
    if tox.get("ames_mutagenicity", 0) > 0.5:
        flags.append("Ames mutagenicity concern")
    if tox.get("hepatotoxicity", 0) > 0.5:
        flags.append("Hepatotoxicity signal")
    if tox.get("oral_rat_ld50", 2000) < 300:
        flags.append("Acute oral toxicity (LD50 < 300 mg/kg)")

    metab = admet.metabolism
    cyp_inhibitors = [k for k, v in metab.items() if v > 0.5]
    if cyp_inhibitors:
        names = ", ".join(k.replace("_inhibitor", "").upper() for k in cyp_inhibitors)
        flags.append(f"CYP inhibition: {names}")

    if admet.distribution.get("bbb_penetration", 0) > 0.7:
        flags.append("High BBB penetration (CNS exposure)")

    for hit in off_target.off_targets:
        if hit.similarity_score > 0.5:
            flags.append(
                f"Off-target: {hit.protein_name} "
                f"(sim={hit.similarity_score:.2f}, {hit.known_adverse_effects})"
            )

    return flags


def _classify_risk(score: float) -> str:
    """Map numeric score to risk category."""
    if score >= 75:
        return "low"
    if score >= 50:
        return "medium"
    return "high"


def _generate_recommendation(
    score: float, risk: str, flags: list[str]
) -> str:
    """Generate human-readable recommendation text."""
    if risk == "low" and not flags:
        return "Compound shows favorable safety profile. Recommend proceeding to lead optimization."

    if risk == "low":
        flag_text = "; ".join(flags[:3])
        return (
            f"Generally favorable safety profile with minor flags: {flag_text}. "
            "Consider targeted assays to confirm."
        )

    if risk == "medium":
        flag_text = "; ".join(flags[:3])
        return (
            f"Moderate safety concerns identified: {flag_text}. "
            "Recommend structural optimization to mitigate liabilities before advancing."
        )

    flag_text = "; ".join(flags[:3])
    return (
        f"Significant safety liabilities detected: {flag_text}. "
        "Recommend deprioritization or major structural redesign."
    )


class SafetyScorer:
    """Orchestrates ADMET and off-target analysis into a unified safety score."""

    def __init__(
        self,
        admet_api_url: str | None = None,
        admet_api_key: str | None = None,
        similarity_threshold: float = 0.25,
    ) -> None:
        self._admet = ADMETPredictor(api_url=admet_api_url, api_key=admet_api_key)
        self._off_target = OffTargetAnalyzer(similarity_threshold=similarity_threshold)

    def score_drug(
        self,
        smiles: str,
        drug_name: str,
        target_sequence: str | None = None,
    ) -> SafetyReport:
        """Run full safety assessment on a single compound.

        Args:
            smiles: SMILES string of the drug candidate.
            drug_name: Human-readable name.
            target_sequence: Optional primary target protein sequence.

        Returns:
            SafetyReport with combined scoring and regulatory flags.
        """
        if not smiles or not smiles.strip():
            raise ValueError("SMILES string cannot be empty")

        admet_result = self._admet.predict_admet(smiles)
        off_target_result = self._off_target.analyze_off_targets(
            smiles, target_sequence or ""
        )

        # Weighted combination: ADMET 60%, off-target 40%
        admet_score = admet_result.overall_safety_score * 100
        ot_hits = off_target_result.num_potential_off_targets
        max_sim = max(
            (h.similarity_score for h in off_target_result.off_targets), default=0
        )
        ot_score = max(0, 100 - ot_hits * 8 - max_sim * 40)

        combined = round(admet_score * 0.6 + ot_score * 0.4, 1)
        combined = max(0, min(100, combined))

        risk = _classify_risk(combined)
        flags = _generate_regulatory_flags(admet_result, off_target_result)
        recommendation = _generate_recommendation(combined, risk, flags)

        return SafetyReport(
            drug_name=drug_name,
            smiles=smiles,
            admet=admet_result,
            off_targets=off_target_result,
            overall_score=combined,
            risk_level=risk,
            regulatory_flags=flags,
            recommendation=recommendation,
        )

    def batch_score(self, drug_list: list[dict]) -> list[SafetyReport]:
        """Score multiple drugs.

        Args:
            drug_list: List of dicts with keys 'smiles', 'name', and optional
                       'target_sequence'.

        Returns:
            List of SafetyReport objects.
        """
        results: list[SafetyReport] = []
        for entry in drug_list:
            smiles = entry.get("smiles", "")
            name = entry.get("name", "unknown")
            target = entry.get("target_sequence")
            try:
                report = self.score_drug(smiles, name, target)
                results.append(report)
            except Exception as exc:
                logger.error("Failed to score %s: %s", name, exc)
                results.append(SafetyReport(
                    drug_name=name,
                    smiles=smiles,
                    risk_level="error",
                    recommendation=f"Scoring failed: {exc}",
                ))
        return results

    def score_demo_antibiotics(self) -> list[SafetyReport]:
        """Run safety scoring on built-in demo antibiotic set.

        Returns:
            List of SafetyReport for common antibiotics.
        """
        drug_list = [
            {"smiles": d["smiles"], "name": d["name"]}
            for d in DEMO_DRUGS.values()
        ]
        return self.batch_score(drug_list)
