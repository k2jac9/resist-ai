"""Tests for the src/pipeline/safety_prediction subpackage.

Covers the ADMET predictor, off-target analyzer, and the SafetyScorer that
combines them. All deterministic and offline (RDKit heuristic path, no API).
"""
import pytest

from src.pipeline.safety_prediction.admet_predictor import (
    ADMETPredictor,
    ADMETResult,
    _calculate_safety_score,
    _placeholder_descriptors,
    _sigmoid,
)
from src.pipeline.safety_prediction.off_target_analyzer import (
    ANTI_TARGETS,
    OffTarget,
    OffTargetAnalyzer,
    _classify_risk as _ot_classify_risk,
    _compute_tanimoto,
    _fallback_similarity,
)
from src.pipeline.safety_prediction.safety_scorer import (
    DEMO_DRUGS,
    SafetyReport,
    SafetyScorer,
    _classify_risk,
)

ASPIRIN = "CC(=O)OC1=CC=CC=C1C(=O)O"


# -- ADMET predictor -----------------------------------------------------------

class TestADMETPredictor:
    def test_empty_smiles_raises(self):
        with pytest.raises(ValueError):
            ADMETPredictor().predict_admet("  ")

    def test_invalid_smiles_raises(self):
        with pytest.raises(ValueError):
            ADMETPredictor().predict_admet("NOT_A_MOLECULE!!!")

    def test_heuristic_result_shape(self):
        r = ADMETPredictor().predict_admet(ASPIRIN)
        assert isinstance(r, ADMETResult)
        assert {"caco2_permeability", "human_intestinal_absorption", "pgp_substrate"} \
            <= set(r.absorption)
        assert {"herg_inhibition", "ames_mutagenicity", "hepatotoxicity",
                "skin_sensitization", "oral_rat_ld50"} <= set(r.toxicity)
        assert 0.0 <= r.overall_safety_score <= 1.0

    def test_deterministic(self):
        a = ADMETPredictor().predict_admet(ASPIRIN)
        b = ADMETPredictor().predict_admet(ASPIRIN)
        assert a.overall_safety_score == b.overall_safety_score
        assert a.toxicity == b.toxicity

    def test_no_api_configured_uses_heuristic(self):
        p = ADMETPredictor()
        assert p._api_available is False

    def test_api_flag_set_when_url_and_key_given(self):
        p = ADMETPredictor(api_url="https://x", api_key="k")
        assert p._api_available is True


class TestADMETHelpers:
    def test_sigmoid_bounds(self):
        assert _sigmoid(0) == 0.5
        assert _sigmoid(1000) == pytest.approx(1.0)
        assert _sigmoid(-1000) == pytest.approx(0.0)

    def test_placeholder_descriptors_keys(self):
        d = _placeholder_descriptors(ASPIRIN)
        for key in ("mw", "logp", "tpsa", "hbd", "hba", "heavy_atoms",
                    "toxicophore_count", "ring_count"):
            assert key in d

    def test_calculate_safety_score_bounded(self):
        clean = ADMETResult(
            absorption={"human_intestinal_absorption": 90},
            toxicity={"herg_inhibition": 0, "ames_mutagenicity": 0,
                      "hepatotoxicity": 0, "skin_sensitization": 0,
                      "oral_rat_ld50": 2000},
        )
        toxic = ADMETResult(
            absorption={"human_intestinal_absorption": 10},
            toxicity={"herg_inhibition": 1, "ames_mutagenicity": 1,
                      "hepatotoxicity": 1, "skin_sensitization": 1,
                      "oral_rat_ld50": 100},
        )
        clean_score = _calculate_safety_score(clean)
        toxic_score = _calculate_safety_score(toxic)
        assert 0.0 <= toxic_score < clean_score <= 1.0


# -- Off-target analyzer -------------------------------------------------------

class TestOffTargetAnalyzer:
    def test_empty_smiles_raises(self):
        with pytest.raises(ValueError):
            OffTargetAnalyzer().analyze_off_targets("")

    def test_analyze_returns_sorted_hits(self):
        report = OffTargetAnalyzer(similarity_threshold=0.1).analyze_off_targets(ASPIRIN)
        assert report.num_potential_off_targets == len(report.off_targets)
        sims = [h.similarity_score for h in report.off_targets]
        assert sims == sorted(sims, reverse=True)

    def test_high_threshold_filters_hits(self):
        low = OffTargetAnalyzer(similarity_threshold=0.05).analyze_off_targets(ASPIRIN)
        high = OffTargetAnalyzer(similarity_threshold=0.95).analyze_off_targets(ASPIRIN)
        assert high.num_potential_off_targets <= low.num_potential_off_targets

    def test_aspirin_flags_cox1(self):
        # Aspirin's exact binder is in the COX-1 panel entry -> self-similarity 1.0.
        report = OffTargetAnalyzer(similarity_threshold=0.3).analyze_off_targets(ASPIRIN)
        assert any("COX-1" in h.protein_name for h in report.off_targets)
        assert report.risk_level == "high"

    def test_risk_classification(self):
        assert _ot_classify_risk([]) == "low"
        high = [OffTarget("X", 0.7, "Liver", "none")]
        assert _ot_classify_risk(high) == "high"
        cardiac = [OffTarget("hERG", 0.45, "Heart", "arrhythmia")]
        assert _ot_classify_risk(cardiac) == "high"
        medium = [OffTarget("X", 0.4, "Liver", "none")]
        assert _ot_classify_risk(medium) == "medium"


class TestSimilarityHelpers:
    def test_tanimoto_self_is_one(self):
        assert _compute_tanimoto(ASPIRIN, ASPIRIN) == 1.0

    def test_tanimoto_invalid_is_zero(self):
        assert _compute_tanimoto("???", "???") == 0.0

    def test_fallback_similarity(self):
        assert _fallback_similarity("", "abc") == 0.0
        assert _fallback_similarity("abc", "abc") == 1.0
        assert 0.0 < _fallback_similarity("abc", "abd") < 1.0

    def test_anti_target_panel_well_formed(self):
        for entry in ANTI_TARGETS:
            assert {"protein", "tissue", "adverse", "binder_smiles"} <= set(entry)


# -- SafetyScorer --------------------------------------------------------------

class TestSafetyScorer:
    def test_score_drug_shape(self):
        report = SafetyScorer().score_drug(ASPIRIN, "Aspirin")
        assert isinstance(report, SafetyReport)
        assert report.drug_name == "Aspirin"
        assert 0.0 <= report.overall_score <= 100.0
        assert report.risk_level in ("low", "medium", "high")
        assert report.admet is not None
        assert report.off_targets is not None

    def test_empty_smiles_raises(self):
        with pytest.raises(ValueError):
            SafetyScorer().score_drug("", "X")

    def test_batch_score_handles_failures(self):
        reports = SafetyScorer().batch_score([
            {"smiles": ASPIRIN, "name": "Aspirin"},
            {"smiles": "", "name": "Broken"},
        ])
        assert len(reports) == 2
        broken = next(r for r in reports if r.drug_name == "Broken")
        assert broken.risk_level == "error"

    def test_classify_risk_thresholds(self):
        assert _classify_risk(80) == "low"
        assert _classify_risk(60) == "medium"
        assert _classify_risk(10) == "high"

    def test_demo_antibiotics_all_scored(self):
        reports = SafetyScorer().score_demo_antibiotics()
        assert len(reports) == len(DEMO_DRUGS)
        assert all(isinstance(r, SafetyReport) for r in reports)
