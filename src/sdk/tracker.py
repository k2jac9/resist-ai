"""Experiment tracking for ResistAI pipeline runs.

SQLite-backed logger that records every pipeline run, prediction,
and molecule candidate for building proprietary datasets over time.
"""
from __future__ import annotations

import csv
import json
import os
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Generator

_DEFAULT_DB = ".resistai/experiments.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS experiments (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    pathogen TEXT DEFAULT '',
    status TEXT DEFAULT 'running',
    duration_ms REAL DEFAULT 0,
    models_used TEXT DEFAULT '[]',
    metadata TEXT DEFAULT '{}',
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment_id TEXT NOT NULL,
    model TEXT NOT NULL,
    input_type TEXT DEFAULT '',
    input_data TEXT DEFAULT '{}',
    output_data TEXT DEFAULT '{}',
    score REAL DEFAULT 0,
    elapsed_ms REAL DEFAULT 0,
    created_at REAL NOT NULL,
    FOREIGN KEY (experiment_id) REFERENCES experiments(id)
);

CREATE TABLE IF NOT EXISTS molecules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment_id TEXT NOT NULL,
    smiles TEXT NOT NULL,
    source TEXT DEFAULT 'generated',
    qed_score REAL DEFAULT 0,
    binding_score REAL DEFAULT 0,
    lipinski_pass INTEGER DEFAULT 0,
    parent_smiles TEXT DEFAULT '',
    generation INTEGER DEFAULT 0,
    created_at REAL NOT NULL,
    FOREIGN KEY (experiment_id) REFERENCES experiments(id)
);
"""


class ExperimentTracker:
    """SQLite-backed experiment tracker."""

    def __init__(self, db_path: str = _DEFAULT_DB) -> None:
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self._db_path = db_path
        # check_same_thread=False allows cross-thread use (e.g. parallel batch
        # runs); the connection is not thread-safe on its own, so every access
        # is serialised through this lock.
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)

    def start_experiment(
        self, name: str, pathogen: str = "", metadata: dict | None = None
    ) -> str:
        eid = uuid.uuid4().hex[:12]
        with self._lock:
            self._conn.execute(
                "INSERT INTO experiments (id, name, pathogen, metadata, created_at) VALUES (?,?,?,?,?)",
                (eid, name, pathogen, json.dumps(metadata or {}), time.time()),
            )
            self._conn.commit()
        return eid

    def log_prediction(
        self,
        experiment_id: str,
        model: str,
        input_data: dict,
        output_data: dict,
        score: float = 0.0,
        elapsed_ms: float = 0.0,
        input_type: str = "",
    ) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO predictions (experiment_id, model, input_type, input_data, output_data, score, elapsed_ms, created_at) VALUES (?,?,?,?,?,?,?,?)",
                (experiment_id, model, input_type, json.dumps(input_data), json.dumps(output_data), score, elapsed_ms, time.time()),
            )
            self._conn.commit()

    def log_molecule(
        self,
        experiment_id: str,
        smiles: str,
        source: str = "generated",
        qed_score: float = 0.0,
        binding_score: float = 0.0,
        lipinski_pass: bool = False,
        parent_smiles: str = "",
        generation: int = 0,
    ) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO molecules (experiment_id, smiles, source, qed_score, binding_score, lipinski_pass, parent_smiles, generation, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (experiment_id, smiles, source, qed_score, binding_score, int(lipinski_pass), parent_smiles, generation, time.time()),
            )
            self._conn.commit()

    def end_experiment(
        self,
        experiment_id: str,
        status: str = "completed",
        duration_ms: float = 0.0,
        models_used: list[str] | None = None,
    ) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE experiments SET status=?, duration_ms=?, models_used=? WHERE id=?",
                (status, duration_ms, json.dumps(models_used or []), experiment_id),
            )
            self._conn.commit()

    def get_experiment(self, experiment_id: str) -> dict[str, Any]:
        with self._lock:
            row = self._conn.execute("SELECT * FROM experiments WHERE id=?", (experiment_id,)).fetchone()
            if not row:
                return {}
            exp = dict(row)
            exp["models_used"] = json.loads(exp.get("models_used", "[]"))
            exp["metadata"] = json.loads(exp.get("metadata", "{}"))
            exp["predictions"] = [
                {**dict(r), "input_data": json.loads(r["input_data"]), "output_data": json.loads(r["output_data"])}
                for r in self._conn.execute("SELECT * FROM predictions WHERE experiment_id=? ORDER BY created_at", (experiment_id,))
            ]
            exp["molecules"] = [
                dict(r) for r in self._conn.execute("SELECT * FROM molecules WHERE experiment_id=? ORDER BY binding_score DESC", (experiment_id,))
            ]
            return exp

    def list_experiments(self, limit: int = 50) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, name, pathogen, status, duration_ms, models_used, created_at FROM experiments ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["models_used"] = json.loads(d.get("models_used", "[]"))
            results.append(d)
        return results

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            exp_count = self._conn.execute("SELECT COUNT(*) FROM experiments").fetchone()[0]
            pred_count = self._conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]
            mol_count = self._conn.execute("SELECT COUNT(*) FROM molecules").fetchone()[0]
            avg_binding = self._conn.execute("SELECT AVG(binding_score) FROM molecules WHERE binding_score > 0").fetchone()[0] or 0
            avg_qed = self._conn.execute("SELECT AVG(qed_score) FROM molecules WHERE qed_score > 0").fetchone()[0] or 0
            top_models = self._conn.execute(
                "SELECT model, COUNT(*) as cnt FROM predictions GROUP BY model ORDER BY cnt DESC LIMIT 5"
            ).fetchall()
        return {
            "total_experiments": exp_count,
            "total_predictions": pred_count,
            "total_molecules": mol_count,
            "avg_binding_score": round(avg_binding, 4),
            "avg_qed_score": round(avg_qed, 4),
            "top_models": [{"model": r[0], "count": r[1]} for r in top_models],
        }

    def export_molecules_csv(self, output_path: str) -> int:
        with self._lock:
            rows = self._conn.execute(
                "SELECT m.smiles, m.source, m.qed_score, m.binding_score, m.lipinski_pass, "
                "m.parent_smiles, m.generation, e.pathogen, e.name as experiment "
                "FROM molecules m JOIN experiments e ON m.experiment_id = e.id "
                "ORDER BY m.binding_score DESC"
            ).fetchall()
        with open(output_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["smiles", "source", "qed_score", "binding_score", "lipinski_pass", "parent_smiles", "generation", "pathogen", "experiment"])
            for r in rows:
                writer.writerow(list(r))
        return len(rows)

    @contextmanager
    def experiment(self, name: str, pathogen: str = "", metadata: dict | None = None) -> Generator[_ExperimentContext, None, None]:
        eid = self.start_experiment(name, pathogen, metadata)
        ctx = _ExperimentContext(self, eid)
        t0 = time.time()
        try:
            yield ctx
            elapsed = (time.time() - t0) * 1000
            self.end_experiment(eid, "completed", elapsed, ctx.models_used)
        except Exception:
            elapsed = (time.time() - t0) * 1000
            self.end_experiment(eid, "failed", elapsed, ctx.models_used)
            raise

    def close(self) -> None:
        self._conn.close()


class _ExperimentContext:
    """Context object yielded by ExperimentTracker.experiment()."""

    def __init__(self, tracker: ExperimentTracker, experiment_id: str) -> None:
        self._tracker = tracker
        self.experiment_id = experiment_id
        self.models_used: list[str] = []

    def log_prediction(self, model: str, input_data: dict, output_data: dict,
                       score: float = 0.0, elapsed_ms: float = 0.0) -> None:
        if model not in self.models_used:
            self.models_used.append(model)
        self._tracker.log_prediction(self.experiment_id, model, input_data, output_data, score, elapsed_ms)

    def log_molecule(self, smiles: str, source: str = "generated", qed_score: float = 0.0,
                     binding_score: float = 0.0, lipinski_pass: bool = False,
                     parent_smiles: str = "", generation: int = 0) -> None:
        self._tracker.log_molecule(self.experiment_id, smiles, source, qed_score, binding_score, lipinski_pass, parent_smiles, generation)
