"""Tests for the SQLite-backed ExperimentTracker."""
import csv

import pytest

from src.sdk.tracker import ExperimentTracker


@pytest.fixture
def tracker(tmp_path):
    t = ExperimentTracker(db_path=str(tmp_path / "exp.db"))
    yield t
    t.close()


def test_start_and_get_experiment(tracker):
    eid = tracker.start_experiment("run1", pathogen="kpneu", metadata={"k": "v"})
    assert len(eid) == 12
    exp = tracker.get_experiment(eid)
    assert exp["name"] == "run1"
    assert exp["pathogen"] == "kpneu"
    assert exp["metadata"] == {"k": "v"}
    assert exp["status"] == "running"


def test_get_missing_experiment_returns_empty(tracker):
    assert tracker.get_experiment("does-not-exist") == {}


def test_log_prediction_roundtrips_json(tracker):
    eid = tracker.start_experiment("run")
    tracker.log_prediction(eid, "boltz2", {"smiles": "CCO"}, {"conf": 0.9}, score=0.9)
    exp = tracker.get_experiment(eid)
    assert len(exp["predictions"]) == 1
    pred = exp["predictions"][0]
    assert pred["model"] == "boltz2"
    assert pred["input_data"] == {"smiles": "CCO"}
    assert pred["output_data"] == {"conf": 0.9}


def test_log_molecule_sorted_by_binding(tracker):
    eid = tracker.start_experiment("run")
    tracker.log_molecule(eid, "CCO", binding_score=0.5, lipinski_pass=True)
    tracker.log_molecule(eid, "CCCO", binding_score=0.9)
    exp = tracker.get_experiment(eid)
    smiles = [m["smiles"] for m in exp["molecules"]]
    assert smiles == ["CCCO", "CCO"]  # descending by binding_score
    assert exp["molecules"][1]["lipinski_pass"] == 1  # bool -> int


def test_list_experiments_orders_newest_first(tracker):
    a = tracker.start_experiment("a")
    b = tracker.start_experiment("b")
    listed = [e["id"] for e in tracker.list_experiments()]
    assert listed[:2] == [b, a]


def test_get_stats_aggregates(tracker):
    eid = tracker.start_experiment("run")
    tracker.log_prediction(eid, "boltz2", {}, {})
    tracker.log_prediction(eid, "boltz2", {}, {})
    tracker.log_molecule(eid, "CCO", qed_score=0.8, binding_score=0.6)
    stats = tracker.get_stats()
    assert stats["total_experiments"] == 1
    assert stats["total_predictions"] == 2
    assert stats["total_molecules"] == 1
    assert stats["avg_qed_score"] == pytest.approx(0.8)
    assert stats["top_models"][0] == {"model": "boltz2", "count": 2}


def test_export_csv(tracker, tmp_path):
    eid = tracker.start_experiment("run", pathogen="kpneu")
    tracker.log_molecule(eid, "CCO", binding_score=0.6)
    out = tmp_path / "mols.csv"
    n = tracker.export_molecules_csv(str(out))
    assert n == 1
    rows = list(csv.DictReader(out.open()))
    assert rows[0]["smiles"] == "CCO"
    assert rows[0]["pathogen"] == "kpneu"


def test_context_manager_marks_completed(tracker):
    with tracker.experiment("ctx", pathogen="kpneu") as ctx:
        ctx.log_prediction("evo2", {}, {})
        ctx.log_prediction("evo2", {}, {})  # duplicate model not double-counted
        eid = ctx.experiment_id
    assert ctx.models_used == ["evo2"]
    exp = tracker.get_experiment(eid)
    assert exp["status"] == "completed"
    assert exp["duration_ms"] >= 0
    assert exp["models_used"] == ["evo2"]


def test_context_manager_marks_failed_and_reraises(tracker):
    captured = {}
    with pytest.raises(RuntimeError):
        with tracker.experiment("boom") as ctx:
            captured["id"] = ctx.experiment_id
            raise RuntimeError("kaboom")
    exp = tracker.get_experiment(captured["id"])
    assert exp["status"] == "failed"
