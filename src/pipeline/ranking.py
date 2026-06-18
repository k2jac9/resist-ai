"""Final ranking: combine screening hits and safety reports into DrugCandidates."""
from __future__ import annotations

from ..models.schemas import DrugCandidate, SafetyReport, ScreeningHit


def rank_candidates(
    hits: list[ScreeningHit],
    safety_reports: list[SafetyReport],
) -> list[DrugCandidate]:
    """Combine screening and safety data into a ranked DrugCandidate list."""
    safety_map = {r.drug_name: r for r in safety_reports}
    candidates: list[DrugCandidate] = []
    for hit in hits:
        report = safety_map.get(hit.drug_name)
        safety = report.safety_score if report else 0.5
        overall = round(
            0.5 * hit.binding_affinity + 0.3 * safety + 0.2 * hit.confidence, 4
        )
        pathway = "505(b)(2)" if hit.clinical_phase in ("Approved", "Phase 3") else "505(b)(1)"
        candidates.append(DrugCandidate(
            rank=0,
            drug_name=hit.drug_name,
            smiles=hit.smiles,
            target_name=hit.target_name,
            binding_affinity=hit.binding_affinity,
            safety_score=safety,
            overall_score=overall,
            regulatory_pathway=pathway,
            confidence=hit.confidence,
        ))
    candidates.sort(key=lambda c: c.overall_score, reverse=True)
    for i, c in enumerate(candidates):
        c.rank = i + 1
    return candidates
