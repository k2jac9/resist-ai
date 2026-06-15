"""Tests for FDA regulatory pathway prediction and document generation."""
from datetime import date

import pytest

from src.models.schemas import DrugCandidate
from src.utils.regulatory import (
    calculate_timeline_with_accelerations,
    generate_preind_briefing_document,
    generate_regulatory_report,
    predict_regulatory_pathway,
)


class TestPredictPathway:
    def test_biologic_is_bla(self):
        p = predict_regulatory_pathway("novel binder", is_biologic=True)
        assert p.pathway_type == "BLA"

    def test_novel_molecule_is_505b1(self):
        p = predict_regulatory_pathway("XYZ-001", is_novel_molecule=True)
        assert p.pathway_type == "505(b)(1)"
        assert len(p.timeline_years) == 2

    def test_qidp_always_offered(self):
        p = predict_regulatory_pathway("XYZ-001", is_novel_molecule=True)
        assert any("QIDP" in opt for opt in p.accelerated_options)


class TestTimelineAccelerations:
    def test_accelerations_reduce_timeline(self):
        base = predict_regulatory_pathway("XYZ", is_novel_molecule=True)
        out = calculate_timeline_with_accelerations(
            base, qidp=True, fast_track=True, breakthrough=True
        )
        acc_min, acc_max = out["accelerated_timeline"]
        assert acc_min <= base.timeline_years[0]
        assert acc_max <= base.timeline_years[1]
        assert out["acceleration_factor"] > 0
        assert "QIDP" in out["programs_applied"]

    def test_no_accelerations_is_identity(self):
        base = predict_regulatory_pathway("XYZ", is_novel_molecule=True)
        out = calculate_timeline_with_accelerations(base)
        assert out["accelerated_timeline"] == pytest.approx(base.timeline_years, abs=0.1)
        assert out["programs_applied"] == []


class TestBriefingDocument:
    def _report(self):
        cand = DrugCandidate(
            rank=1, drug_name="ResistX-1", smiles="CCO", target_name="NDM-1",
            overall_score=0.9,
        )
        return generate_regulatory_report(cand)

    def test_document_generated_is_a_date_not_a_tuple(self):
        # Regression: this field used to print the timeline_years tuple.
        doc = generate_preind_briefing_document(self._report())
        gen_line = next(
            line for line in doc.splitlines() if "Document Generated:" in line
        )
        assert date.today().isoformat() in gen_line
        assert "(" not in gen_line  # no stray tuple

    def test_document_includes_drug_and_pathway(self):
        doc = generate_preind_briefing_document(self._report())
        assert "ResistX-1" in doc
        assert "Estimated Timeline:" in doc
