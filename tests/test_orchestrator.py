"""Tests for PipelineOrchestrator and sub-components.

NIM and LLM clients are fully mocked so these run offline.
"""
from unittest.mock import MagicMock, patch

import pytest

from src.pipeline.orchestrator import (
    PipelineOrchestrator,
    SafetyScorer,
    DrugScreener,
    TargetAnalyzer,
)
from src.models.schemas import ScreeningHit, TargetResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def target():
    return TargetResult(
        name="NDM-1",
        pdb_code="3S0Z",
        uniprot_id="B3GCM2",
        function="Metallo-beta-lactamase",
        druggability_score=0.85,
        pathogen="Klebsiella pneumoniae",
        resistance_mechanism="Beta-lactam hydrolysis",
    )


@pytest.fixture
def hit():
    return ScreeningHit(
        rank=1,
        drug_name="Taniborbactam",
        smiles="OB(O)C1CCC(CC(=O)NC2CCNC2)CC1",
        target_name="NDM-1",
        binding_affinity=0.78,
        confidence=0.72,
        mechanism_of_action="Bicyclic boronate BLI",
        clinical_phase="Phase 3",
    )


def _make_orchestrator(nim=None, llm=None):
    """Return a PipelineOrchestrator with NIM/LLM mocked away."""
    orch = PipelineOrchestrator()
    # Patch module-level lazy singletons used inside orchestrator
    if nim:
        patch("src.pipeline.orchestrator._nim", nim).start()
    if llm:
        patch("src.pipeline.orchestrator._llm", llm).start()
    return orch


# ---------------------------------------------------------------------------
# TargetAnalyzer
# ---------------------------------------------------------------------------

class TestTargetAnalyzer:
    def test_discover_targets_returns_list(self):
        analyzer = TargetAnalyzer()
        with patch("src.pipeline.orchestrator._get_nim", return_value=None):
            targets = analyzer.discover_targets("Klebsiella pneumoniae", use_nim=False)
        assert isinstance(targets, list)
        assert len(targets) > 0

    def test_targets_have_druggability_scores(self):
        analyzer = TargetAnalyzer()
        with patch("src.pipeline.orchestrator._get_nim", return_value=None):
            targets = analyzer.discover_targets("Klebsiella pneumoniae", use_nim=False)
        for t in targets:
            assert 0.0 <= t.druggability_score <= 1.0

    def test_targets_sorted_descending(self):
        analyzer = TargetAnalyzer()
        with patch("src.pipeline.orchestrator._get_nim", return_value=None):
            targets = analyzer.discover_targets("Klebsiella pneumoniae", use_nim=False)
        scores = [t.druggability_score for t in targets]
        assert scores == sorted(scores, reverse=True)

    def test_unknown_pathogen_returns_generic_targets(self):
        analyzer = TargetAnalyzer()
        with patch("src.pipeline.orchestrator._get_nim", return_value=None):
            targets = analyzer.discover_targets("UnknownBug XYZ", use_nim=False)
        assert len(targets) > 0


# ---------------------------------------------------------------------------
# DrugScreener
# ---------------------------------------------------------------------------

class TestDrugScreener:
    def test_screen_returns_hits(self, target):
        screener = DrugScreener()
        with patch("src.pipeline.orchestrator._get_nim", return_value=None):
            results = screener.screen_drugs(target, max_drugs=5, use_nim=False)
        assert results.compounds_screened == 5
        assert len(results.hits) == 5

    def test_hits_ranked_by_affinity(self, target):
        screener = DrugScreener()
        with patch("src.pipeline.orchestrator._get_nim", return_value=None):
            results = screener.screen_drugs(target, max_drugs=5, use_nim=False)
        affinities = [h.binding_affinity for h in results.hits]
        assert affinities == sorted(affinities, reverse=True)

    def test_hits_have_smiles(self, target):
        screener = DrugScreener()
        with patch("src.pipeline.orchestrator._get_nim", return_value=None):
            results = screener.screen_drugs(target, max_drugs=3, use_nim=False)
        for h in results.hits:
            assert h.smiles


# ---------------------------------------------------------------------------
# SafetyScorer
# ---------------------------------------------------------------------------

class TestSafetyScorer:
    def test_score_returns_safety_report(self, hit):
        scorer = SafetyScorer()
        report = scorer.score_drug(hit)
        assert report.drug_name == "Taniborbactam"
        assert 0.0 <= report.safety_score <= 1.0

    def test_admet_fields_populated(self, hit):
        scorer = SafetyScorer()
        report = scorer.score_drug(hit)
        admet = report.admet
        assert admet is not None
        for field in ("absorption", "distribution", "metabolism", "excretion"):
            assert 0.0 <= getattr(admet, field) <= 1.0

    def test_off_target_report_present(self, hit):
        scorer = SafetyScorer()
        report = scorer.score_drug(hit)
        assert report.off_target_report is not None
        assert report.off_target_report.overall_risk in ("low", "high")


# ---------------------------------------------------------------------------
# PipelineOrchestrator.run_full_pipeline
# ---------------------------------------------------------------------------

class TestPipelineOrchestrator:
    def _run(self, pathogen="Klebsiella pneumoniae", **kwargs):
        orch = PipelineOrchestrator()
        with patch("src.pipeline.orchestrator._get_nim", return_value=None), \
             patch("src.pipeline.orchestrator._get_llm", return_value=None):
            return orch.run_full_pipeline(
                pathogen_name=pathogen,
                max_drugs=5,
                generate_novel=False,
                **kwargs,
            )

    def test_returns_pipeline_results(self):
        from src.models.schemas import PipelineResults
        result = self._run()
        assert isinstance(result, PipelineResults)

    def test_top_candidates_populated(self):
        result = self._run()
        assert len(result.top_candidates) > 0

    def test_targets_discovered(self):
        result = self._run()
        assert len(result.targets) > 0

    def test_no_targets_raises(self):
        orch = PipelineOrchestrator()
        with patch("src.pipeline.orchestrator._get_nim", return_value=None), \
             patch("src.pipeline.orchestrator._get_llm", return_value=None), \
             patch.object(orch._target_analyzer, "discover_targets", return_value=[]), \
             pytest.raises(ValueError, match="No targets found"):
            orch.run_full_pipeline(
                pathogen_name="FakeBug",
                max_drugs=5,
                generate_novel=False,
            )

    def test_progress_callback_called(self):
        events: list[str] = []

        def cb(stage, pct, msg):
            events.append(stage)

        orch = PipelineOrchestrator(progress_callback=cb)
        with patch("src.pipeline.orchestrator._get_nim", return_value=None), \
             patch("src.pipeline.orchestrator._get_llm", return_value=None):
            orch.run_full_pipeline("Klebsiella pneumoniae", max_drugs=3, generate_novel=False)

        assert "targets" in events
        assert "screening" in events
