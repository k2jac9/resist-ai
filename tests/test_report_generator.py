"""Tests for the markdown/JSON ReportGenerator (pure, no LLM)."""
import json
import os

from src.models.schemas import DrugCandidate, PipelineResults, TargetResult
from src.pipeline.report_generator import ReportGenerator


def _cand(name, rank=1, pathway="505(b)(2)"):
    return DrugCandidate(
        rank=rank, drug_name=name, smiles="CCO", target_name="NDM-1",
        binding_affinity=0.85, safety_score=0.7, overall_score=0.8,
        regulatory_pathway=pathway, confidence=0.9,
    )


def _results():
    return PipelineResults(
        pathogen="klebsiella_pneumoniae",
        targets=[TargetResult(name="NDM-1", pdb_code="3SPU", function="beta-lactamase",
                              druggability_score=0.82, pathogen="klebsiella_pneumoniae")],
        top_candidates=[_cand("Meropenem"), _cand("Cefiderocol", rank=2, pathway="505(b)(1)")],
        metadata={"duration_seconds": 12, "compounds_screened": 50, "demo_mode": True},
    )


class TestCandidateTable:
    def test_empty(self):
        assert ReportGenerator().generate_candidate_table([]) == "_No candidates._"

    def test_populated(self):
        table = ReportGenerator().generate_candidate_table([_cand("Meropenem")])
        assert "| Rank | Drug |" in table
        assert "Meropenem" in table
        assert "**0.800**" in table  # overall score bolded


class TestSummary:
    def test_contains_key_sections(self):
        summary = ReportGenerator().generate_summary(_results())
        assert "# AMR-AI Pipeline Report" in summary
        assert "klebsiella_pneumoniae" in summary
        assert "NDM-1" in summary
        assert "Demo Mode" in summary
        assert "Top Candidates" in summary


class TestRegulatoryOutline:
    def test_lists_505b2_candidates(self):
        outline = ReportGenerator().generate_regulatory_outline(
            [_cand("Meropenem", pathway="505(b)(2)"), _cand("Novel", rank=2, pathway="505(b)(1)")]
        )
        assert "eligible for 505(b)(2)" in outline
        assert "Meropenem" in outline


class TestExport:
    def test_writes_json_and_markdown(self, tmp_path):
        md_path = ReportGenerator().export_results(_results(), str(tmp_path))
        assert os.path.exists(md_path)
        assert md_path.endswith(".md")
        json_files = list(tmp_path.glob("results_*.json"))
        assert len(json_files) == 1
        data = json.loads(json_files[0].read_text())
        assert data["pathogen"] == "klebsiella_pneumoniae"
        assert "# AMR-AI Pipeline Report" in open(md_path).read()
