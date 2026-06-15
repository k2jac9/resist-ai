"""Tests for batch cross-pathogen aggregation (no network/API)."""
import json

from src.models.schemas import DrugCandidate, PipelineResults, TargetResult
from src.sdk.batch import BatchResults, ComparisonReport


def _cand(name, score, target="NDM-1", binding=0.8, safety=0.7):
    return DrugCandidate(
        rank=1, drug_name=name, smiles="CCO", target_name=target,
        binding_affinity=binding, safety_score=safety, overall_score=score,
    )


def _results(pathogen, candidates, n_targets=1):
    return PipelineResults(
        pathogen=pathogen,
        targets=[TargetResult(name=f"t{i}", pdb_code="3SPU", pathogen=pathogen) for i in range(n_targets)],
        top_candidates=candidates,
    )


class TestComparisonReport:
    def test_broad_spectrum_requires_multiple_pathogens(self):
        report = ComparisonReport(all_candidates={
            "kpneu": [_cand("Meropenem", 0.9), _cand("SoloDrug", 0.8)],
            "abaum": [_cand("Meropenem", 0.7)],
        })
        broad = report.broad_spectrum_candidates(min_pathogens=2)
        names = {b["drug_name"] for b in broad}
        assert "Meropenem" in names
        assert "SoloDrug" not in names
        mero = next(b for b in broad if b["drug_name"] == "Meropenem")
        assert mero["num_pathogens"] == 2
        assert mero["avg_overall_score"] == round((0.9 + 0.7) / 2, 4)

    def test_best_per_pathogen_takes_first(self):
        report = ComparisonReport(all_candidates={
            "kpneu": [_cand("Top", 0.95), _cand("Second", 0.5)],
        })
        best = report.best_per_pathogen()
        assert best["kpneu"]["drug_name"] == "Top"

    def test_best_per_pathogen_skips_empty(self):
        report = ComparisonReport(all_candidates={"kpneu": []})
        assert report.best_per_pathogen() == {}

    def test_format_table_markdown(self):
        report = ComparisonReport(all_candidates={
            "klebsiella_pneumoniae": [_cand("Meropenem", 0.9)],
            "acinetobacter_baumannii": [_cand("Meropenem", 0.8)],
        })
        table = report.format_table()
        assert "## Cross-Pathogen Comparison" in table
        assert "Klebsiella Pneumoniae" in table
        assert "Broad-Spectrum" in table


class TestBatchResults:
    def _batch(self):
        return BatchResults(pathogen_results={
            "kpneu": _results("kpneu", [_cand("A", 0.9), _cand("B", 0.8)], n_targets=2),
            "abaum": _results("abaum", [_cand("A", 0.7)], n_targets=1),
        })

    def test_totals(self):
        b = self._batch()
        assert b.total_targets == 3
        assert b.total_candidates == 3

    def test_cross_reactive_drugs(self):
        names = {d["drug_name"] for d in self._batch().cross_reactive_drugs}
        assert "A" in names  # appears in both pathogens
        assert "B" not in names

    def test_summary_handles_errors(self):
        b = self._batch()
        b.errors["pseudomonas"] = "NIM unavailable"
        summary = b.summary()
        assert "# Batch Pipeline Results" in summary
        assert "NIM unavailable" in summary

    def test_to_json_roundtrips(self):
        data = json.loads(self._batch().to_json())
        assert data["total_targets"] == 3
        assert data["total_candidates"] == 3
        assert set(data["pathogens"].keys()) == {"kpneu", "abaum"}

    def test_empty_batch(self):
        b = BatchResults()
        assert b.total_targets == 0
        assert b.total_candidates == 0
        assert b.cross_reactive_drugs == []
        assert "# Batch Pipeline Results" in b.summary()
