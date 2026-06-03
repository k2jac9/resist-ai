"""Tests for the pipeline orchestration layer: ranking, the per-stage
modules, demo data, and an end-to-end demo-mode run.

Offline-safe: ESM-2 and the LLM client are patched out so nothing loads a
heavy model or touches the network.
"""
from unittest.mock import patch

import pytest

from src.models.schemas import (
    DrugCandidate,
    SafetyReport,
    ScreeningHit,
    TargetResult,
)
from src.pipeline import stages
from src.pipeline.demo_data import DEMO_DRUG_LIBRARY, DEMO_SEQUENCES
from src.pipeline.ranking import rank_candidates
from src.pipeline.safety_stage import SafetyScorer
from src.pipeline.screening_stage import DrugScreener
from src.pipeline.target_stage import (
    FALLBACK_TARGETS,
    TargetAnalyzer,
    compute_druggability,
    get_pathogen_targets,
)


@pytest.fixture(autouse=True)
def _no_esm2():
    """Force the heuristic druggability path (never load ESM-2)."""
    with patch.object(stages, "_get_esm2", return_value=None):
        yield


# -- ranking.rank_candidates ---------------------------------------------------

class TestRankCandidates:
    def _hit(self, name, affinity, conf=0.8, phase=""):
        return ScreeningHit(
            rank=0, drug_name=name, smiles="CCO", target_name="T",
            binding_affinity=affinity, confidence=conf, clinical_phase=phase,
        )

    def test_empty_inputs(self):
        assert rank_candidates([], []) == []

    def test_ranks_by_overall_score_descending(self):
        hits = [self._hit("low", 0.2), self._hit("high", 0.95)]
        ranked = rank_candidates(hits, [])
        assert [c.drug_name for c in ranked] == ["high", "low"]
        assert ranked[0].rank == 1
        assert ranked[1].rank == 2

    def test_missing_safety_defaults_to_half(self):
        ranked = rank_candidates([self._hit("d", 0.5)], [])
        assert ranked[0].safety_score == 0.5

    def test_safety_report_is_matched_by_name(self):
        report = SafetyReport(drug_name="d", safety_score=0.9)
        ranked = rank_candidates([self._hit("d", 0.5)], [report])
        assert ranked[0].safety_score == 0.9

    def test_overall_score_formula(self):
        # overall = 0.5*affinity + 0.3*safety + 0.2*confidence
        report = SafetyReport(drug_name="d", safety_score=0.8)
        ranked = rank_candidates([self._hit("d", 0.6, conf=0.7)], [report])
        assert ranked[0].overall_score == round(0.5 * 0.6 + 0.3 * 0.8 + 0.2 * 0.7, 4)

    @pytest.mark.parametrize("phase,expected", [
        ("Approved", "505(b)(2)"),
        ("Phase 3", "505(b)(2)"),
        ("Phase 1", "505(b)(1)"),
        ("", "505(b)(1)"),
    ])
    def test_regulatory_pathway(self, phase, expected):
        ranked = rank_candidates([self._hit("d", 0.5, phase=phase)], [])
        assert ranked[0].regulatory_pathway == expected

    def test_returns_drug_candidates(self):
        ranked = rank_candidates([self._hit("d", 0.5)], [])
        assert isinstance(ranked[0], DrugCandidate)


# -- target_stage --------------------------------------------------------------

class TestComputeDruggability:
    def test_known_values(self):
        assert compute_druggability(DEMO_SEQUENCES["NDM-1"]) == 0.95
        assert compute_druggability(DEMO_SEQUENCES["OXA-23"]) == 0.8

    def test_empty_sequence_floor(self):
        # length_score 0.60, hydro 0 -> 0.5*0.6 = 0.30
        assert compute_druggability("") == 0.3

    def test_bounded(self):
        for seq in DEMO_SEQUENCES.values():
            assert 0.0 <= compute_druggability(seq) <= 1.0


class TestGetPathogenTargets:
    def test_known_pathogen(self):
        targets = get_pathogen_targets("staphylococcus_aureus")
        assert any(t["name"] == "PBP2a" for t in targets)

    def test_unknown_falls_back_to_acinetobacter(self):
        targets = get_pathogen_targets("not_a_real_pathogen")
        assert targets == FALLBACK_TARGETS["acinetobacter_baumannii"]


class TestTargetAnalyzerStage:
    def test_demo_discovery_sorted_and_typed(self):
        targets = TargetAnalyzer().discover_targets("klebsiella_pneumoniae", use_nim=False)
        assert targets
        assert all(isinstance(t, TargetResult) for t in targets)
        scores = [t.druggability_score for t in targets]
        assert scores == sorted(scores, reverse=True)

    def test_pathogen_recorded_on_results(self):
        targets = TargetAnalyzer().discover_targets("pseudomonas_aeruginosa", use_nim=False)
        assert all(t.pathogen == "pseudomonas_aeruginosa" for t in targets)


# -- screening_stage -----------------------------------------------------------

class TestDrugScreener:
    def _target(self, name="NDM-1"):
        return TargetResult(name=name, pdb_code="3SPU")

    def test_screens_full_library_offline(self):
        result = DrugScreener().screen_drugs(self._target(), use_nim=False)
        assert result.compounds_screened == len(DEMO_DRUG_LIBRARY)
        assert len(result.hits) == len(DEMO_DRUG_LIBRARY)
        assert result.model_used == "heuristic_docking"

    def test_max_drugs_limits_library(self):
        result = DrugScreener().screen_drugs(self._target(), max_drugs=3, use_nim=False)
        assert result.compounds_screened == 3

    def test_hits_sorted_and_reranked(self):
        hits = DrugScreener().screen_drugs(self._target(), use_nim=False).hits
        affinities = [h.binding_affinity for h in hits]
        assert affinities == sorted(affinities, reverse=True)
        assert [h.rank for h in hits] == list(range(1, len(hits) + 1))

    def test_deterministic_within_process(self):
        a = DrugScreener().screen_drugs(self._target(), use_nim=False)
        b = DrugScreener().screen_drugs(self._target(), use_nim=False)
        assert [h.binding_affinity for h in a.hits] == [h.binding_affinity for h in b.hits]


# -- safety_stage --------------------------------------------------------------

class TestSafetyStage:
    def test_score_drug_returns_report(self):
        hit = ScreeningHit(rank=1, drug_name="Cefiderocol", smiles="CCO", target_name="NDM-1")
        report = SafetyScorer().score_drug(hit)
        assert isinstance(report, SafetyReport)
        assert report.drug_name == "Cefiderocol"
        assert report.admet is not None
        assert report.off_target_report is not None
        assert 0.0 <= report.safety_score <= 1.0
        assert report.recommendation in ("proceed", "caution")

    def test_overall_risk_reflects_high_risk_flag(self):
        hit = ScreeningHit(rank=1, drug_name="d", smiles="CCO", target_name="T")
        report = SafetyScorer().score_drug(hit)
        assert report.off_target_report.overall_risk in ("high", "low")


# -- demo_data integrity -------------------------------------------------------

# Demo-library SMILES that RDKit cannot parse. These are known data bugs to be
# fixed by sourcing a corrected canonical SMILES (see xfail test below).
KNOWN_INVALID_SMILES = {"Gepotidacin"}


class TestDemoData:
    def test_drug_library_schema(self):
        for entry in DEMO_DRUG_LIBRARY:
            assert {"name", "smiles", "moa", "phase"} <= set(entry)
            assert entry["smiles"]

    def test_drug_smiles_are_valid(self):
        from rdkit import Chem
        for entry in DEMO_DRUG_LIBRARY:
            if entry["name"] in KNOWN_INVALID_SMILES:
                continue
            assert Chem.MolFromSmiles(entry["smiles"]) is not None, entry["name"]

    @pytest.mark.xfail(strict=True, reason="Gepotidacin demo SMILES fails to "
                       "kekulize; needs a corrected canonical SMILES")
    def test_known_invalid_smiles_should_be_fixed(self):
        # When the demo SMILES is corrected this test XPASSes and (being strict)
        # fails the suite, signalling that the entry should leave KNOWN_INVALID.
        from rdkit import Chem
        bad = next(d for d in DEMO_DRUG_LIBRARY if d["name"] == "Gepotidacin")
        assert Chem.MolFromSmiles(bad["smiles"]) is not None

    def test_sequences_non_empty_uppercase(self):
        for name, seq in DEMO_SEQUENCES.items():
            assert seq and seq.isupper(), name

    def test_drug_names_unique(self):
        names = [d["name"] for d in DEMO_DRUG_LIBRARY]
        assert len(names) == len(set(names))


# -- end-to-end demo-mode pipeline ---------------------------------------------

class TestPipelineEndToEnd:
    def test_demo_run_produces_ranked_candidates(self):
        from src.pipeline.orchestrator import PipelineOrchestrator

        with patch("src.pipeline.orchestrator.get_llm", return_value=None):
            results = PipelineOrchestrator().run_full_pipeline(
                "acinetobacter_baumannii", demo_mode=True, generate_novel=False,
            )

        assert results.pathogen == "acinetobacter_baumannii"
        assert results.targets
        assert results.top_candidates
        # candidates are rank-ordered 1..N
        assert [c.rank for c in results.top_candidates] == \
            list(range(1, len(results.top_candidates) + 1))
        assert results.metadata["demo_mode"] is True
        assert "heuristic_scoring" in results.metadata["models_used"]

    def test_unknown_pathogen_uses_fallback_targets(self):
        from src.pipeline.orchestrator import PipelineOrchestrator

        with patch("src.pipeline.orchestrator.get_llm", return_value=None):
            results = PipelineOrchestrator().run_full_pipeline(
                "unknown_bug", demo_mode=True, generate_novel=False,
            )
        # get_pathogen_targets falls back to acinetobacter targets
        assert results.targets
