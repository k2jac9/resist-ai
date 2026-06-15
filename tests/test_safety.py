"""Tests for the safety_prediction package: ADMET, off-target, and scoring.

These are characterization tests that lock in the deterministic,
structure-derived behavior the audit established (no random numbers; the
same SMILES always yields the same scores).
"""
import pytest

from src.pipeline.safety_prediction.admet_predictor import (
    ADMETPredictor,
    ADMETResult,
    _calculate_safety_score,
)
from src.pipeline.safety_prediction.off_target_analyzer import OffTargetAnalyzer
from src.pipeline.safety_prediction.safety_scorer import SafetyScorer


# -- ADMETPredictor -----------------------------------------------------------

class TestADMETPredictor:
    def test_empty_smiles_raises(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            ADMETPredictor().predict_admet("  ")

    def test_invalid_smiles_raises(self, invalid_smiles):
        with pytest.raises(ValueError, match="Invalid SMILES"):
            ADMETPredictor().predict_admet(invalid_smiles)

    def test_returns_full_result(self, sample_smiles):
        result = ADMETPredictor().predict_admet(sample_smiles)
        assert isinstance(result, ADMETResult)
        for section in (result.absorption, result.distribution,
                        result.metabolism, result.excretion, result.toxicity):
            assert section  # non-empty dict
        assert 0.0 <= result.overall_safety_score <= 1.0

    def test_deterministic(self, sample_smiles):
        a = ADMETPredictor().predict_admet(sample_smiles)
        b = ADMETPredictor().predict_admet(sample_smiles)
        assert a.toxicity == b.toxicity
        assert a.overall_safety_score == b.overall_safety_score

    def test_safety_score_bounded_for_toxic_profile(self):
        toxic = ADMETResult(
            absorption={"human_intestinal_absorption": 90},
            toxicity={
                "herg_inhibition": 1.0, "ames_mutagenicity": 1.0,
                "hepatotoxicity": 1.0, "skin_sensitization": 1.0,
                "oral_rat_ld50": 100,
            },
        )
        score = _calculate_safety_score(toxic)
        assert 0.0 <= score <= 1.0


# -- OffTargetAnalyzer --------------------------------------------------------

class TestOffTargetAnalyzer:
    def test_empty_smiles_raises(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            OffTargetAnalyzer().analyze_off_targets("")

    def test_aspirin_flags_cox1(self, sample_smiles):
        # The COX-1 anti-target binder is aspirin itself, so the panel must
        # flag a near-identical (sim ~1.0) high-risk off-target.
        report = OffTargetAnalyzer().analyze_off_targets(sample_smiles)
        names = {ot.protein_name for ot in report.off_targets}
        assert "COX-1" in names
        assert report.risk_level == "high"

    def test_results_sorted_descending(self, sample_smiles):
        report = OffTargetAnalyzer().analyze_off_targets(sample_smiles)
        sims = [ot.similarity_score for ot in report.off_targets]
        assert sims == sorted(sims, reverse=True)

    def test_deterministic(self, sample_smiles):
        a = OffTargetAnalyzer().analyze_off_targets(sample_smiles)
        b = OffTargetAnalyzer().analyze_off_targets(sample_smiles)
        assert a.num_potential_off_targets == b.num_potential_off_targets
        assert a.risk_level == b.risk_level


# -- SafetyScorer -------------------------------------------------------------

class TestSafetyScorer:
    def test_score_drug_bounds(self, sample_smiles):
        report = SafetyScorer().score_drug(sample_smiles, "Aspirin")
        assert 0.0 <= report.overall_score <= 100.0
        assert report.risk_level in {"low", "medium", "high"}
        assert report.admet is not None
        assert report.off_targets is not None
        assert report.recommendation

    def test_empty_smiles_raises(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            SafetyScorer().score_drug("", "nameless")

    def test_batch_score_isolates_failures(self, sample_smiles, invalid_smiles):
        reports = SafetyScorer().batch_score([
            {"smiles": sample_smiles, "name": "Good"},
            {"smiles": invalid_smiles, "name": "Bad"},
        ])
        assert len(reports) == 2
        by_name = {r.drug_name: r for r in reports}
        assert by_name["Good"].risk_level in {"low", "medium", "high"}
        assert by_name["Bad"].risk_level == "error"

    def test_demo_antibiotics_all_scored(self):
        reports = SafetyScorer().score_demo_antibiotics()
        assert len(reports) == 5
        assert all(r.risk_level != "error" for r in reports)
