"""Conservative, process-safe admission of paid model attempts."""
from __future__ import annotations

import math
import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path


class QuotaExceeded(Exception):
    """The global model-attempt budget does not admit this request."""


class RequestLimits:
    """Charge before inference; never refund an attempted call.

    All workers must share this persistent database. Limits are rolling windows;
    the lifetime counter survives pruning and clock rollback cannot reset a window.
    """

    def __init__(self, path: str, per_minute: int = 4, per_day: int = 40,
                 lifetime: int = 200):
        if not isinstance(path, str) or not Path(path).is_absolute():
            raise ValueError("RESISTAI_QUOTA_DB must be an absolute persistent file path")
        if any(type(value) is not int or value <= 0 for value in (per_minute, per_day, lifetime)):
            raise ValueError("Model attempt limits must be positive integers")
        self.path = path
        self.limits = (per_minute, per_day, lifetime)
        # Do not create missing parent directories: deployment must mount its data volume.
        fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
        os.close(fd)
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("CREATE TABLE IF NOT EXISTS budget (id INTEGER PRIMARY KEY CHECK(id=1), "
                       "total INTEGER NOT NULL, last_clock REAL NOT NULL)")
            db.execute("INSERT OR IGNORE INTO budget VALUES (1, 0, 0)")
            db.execute("CREATE TABLE IF NOT EXISTS attempts (at REAL NOT NULL)")
            db.execute("CREATE INDEX IF NOT EXISTS attempts_at ON attempts(at)")

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        try:
            with db:
                yield db
        finally:
            db.close()

    def reserve(self, *, now: float | None = None) -> None:
        now = time.time() if now is None else now
        if isinstance(now, bool) or not isinstance(now, (int, float)) or not math.isfinite(now) or now < 0:
            raise ValueError("Invalid admission clock")
        denied = False
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            total, last_clock = db.execute("SELECT total, last_clock FROM budget WHERE id=1").fetchone()
            clock = max(now, last_clock)
            minute = db.execute("SELECT count(*) FROM attempts WHERE at >= ?", (clock - 60,)).fetchone()[0]
            day = db.execute("SELECT count(*) FROM attempts WHERE at >= ?", (clock - 86400,)).fetchone()[0]
            denied = any(count >= limit for count, limit in zip((minute, day, total), self.limits))
            db.execute("UPDATE budget SET last_clock=? WHERE id=1", (clock,))
            if not denied:
                db.execute("INSERT INTO attempts VALUES (?)", (clock,))
                db.execute("UPDATE budget SET total=total+1 WHERE id=1")
                db.execute("DELETE FROM attempts WHERE at < ?", (clock - 86400,))
        if denied:
            raise QuotaExceeded("model_attempt_limit_reached")
