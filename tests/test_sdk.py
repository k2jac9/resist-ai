"""Tests for the ResistAI Pipeline SDK -- Target, Pipeline, and PipelineResults."""
import json

import pytest

from src.sdk.target import Target
from src.sdk.pipeline import Pipeline
from src.sdk.results import (
    PipelineResults,
    ScreeningHit,
    NovelMolecule,
)


# -- Target.from_sequence -----------------------------------------------------

class TestTarget:
    def test_from_sequence_basic(self, sample_sequence):
        t = Target.from_sequence(sample_sequence, name="NDM-1")
        assert t.name == "NDM-1"
        assert t.sequence == sample_sequence
        assert t.source == "sequence"
        assert t.length == len(sample_sequence)

    def test_from_sequence_auto_name(self):
        seq = "MELPNIMH"
        t = Target.from_sequence(seq)
        assert t.name == f"seq_{len(seq)}aa"

    def test_from_sequence_strips_whitespace(self):
        t = Target.from_sequence("  MEL PNI MH  ")
        assert t.sequence == "MELPNIMH"

    def test_from_sequence_empty_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            Target.from_sequence("")

    def test_has_structure_false_by_default(self, sample_sequence):
        t = Target.from_sequence(sample_sequence)
        assert t.has_structure is False


# -- Pipeline creation and chaining -------------------------------------------

class TestPipeline:
    def test_creation(self, sample_sequence):
        t = Target.from_sequence(sample_sequence, name="test")
        p = Pipeline(t)
        assert repr(p) == "Pipeline(target='test', steps=[])"

    def test_chaining_returns_self(self, sample_sequence):
        t = Target.from_sequence(sample_sequence, name="test")
        p = Pipeline(t)
        result = p.fold()
        assert result is p

    def test_chaining_accumulates_steps(self, sample_sequence):
        t = Target.from_sequence(sample_sequence, name="test")
        p = Pipeline(t).fold().screen().generate().validate()
        assert "fold" in repr(p)
        assert "screen" in repr(p)
        assert "generate" in repr(p)
        assert "validate" in repr(p)

    def test_step_count(self, sample_sequence):
        t = Target.from_sequence(sample_sequence, name="test")
        p = Pipeline(t).fold().screen().dock().generate()
        assert len(p._steps) == 4


# -- PipelineResults -----------------------------------------------------------

class TestPipelineResults:
    def _make_results(self):
        r = PipelineResults(
            target_name="NDM-1",
            target_sequence="MELPNIMH",
            started_at="2026-03-28T00:00:00Z",
            finished_at="2026-03-28T00:01:00Z",
            steps_executed=["fold", "screen"],
        )
        r.screening_hits.append(ScreeningHit(
            drug_name="Meropenem", smiles="CC(O)=O", confidence=0.85,
        ))
        r.novel_molecules.append(NovelMolecule(
            smiles="CCO", score=0.9, score_type="QED",
        ))
        return r

    def test_to_json_parses(self):
        r = self._make_results()
        j = r.to_json()
        data = json.loads(j)
        assert data["target_name"] == "NDM-1"
        assert len(data["screening_hits"]) == 1
        assert len(data["novel_molecules"]) == 1
        assert data["steps_executed"] == ["fold", "screen"]

    def test_to_dict_keys(self):
        r = self._make_results()
        d = r.to_dict()
        expected_keys = {
            "target_name", "target_sequence_length", "started_at",
            "finished_at", "steps_executed", "structure_available",
            "structure_length", "fold_elapsed_ms", "screening_hits",
            "docking_poses", "novel_molecules", "validated_molecules",
            "binder_design", "analysis", "errors",
        }
        assert expected_keys.issubset(set(d.keys()))

    def test_to_report_returns_markdown(self):
        r = self._make_results()
        report = r.to_report()
        assert isinstance(report, str)
        assert "# ResistAI Pipeline Report" in report
        assert "NDM-1" in report
        assert "Meropenem" in report

    def test_empty_results_serialize(self):
        r = PipelineResults()
        j = r.to_json()
        data = json.loads(j)
        assert data["target_name"] == ""
        assert data["screening_hits"] == []
