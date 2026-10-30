"""Durable admission behavior; runs with the Python standard library alone."""
import multiprocessing
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from src.request_limits import QuotaExceeded, RequestLimits


def _reserve_in_process(path, queue):
    limiter = RequestLimits(path, per_minute=3, per_day=10, lifetime=10)
    try:
        limiter.reserve(now=1000)
        queue.put(True)
    except QuotaExceeded:
        queue.put(False)


class RequestLimitsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = str(Path(self.temp.name) / "attempts.sqlite3")

    def test_restart_preserves_attempts(self):
        RequestLimits(self.path, 1, 10, 10).reserve(now=1000)
        with self.assertRaises(QuotaExceeded):
            RequestLimits(self.path, 1, 10, 10).reserve(now=1001)

    def test_rolling_windows_and_lifetime(self):
        limiter = RequestLimits(self.path, 1, 2, 3)
        limiter.reserve(now=1000)
        with self.assertRaises(QuotaExceeded):
            limiter.reserve(now=1060)
        limiter.reserve(now=1061)
        with self.assertRaises(QuotaExceeded):
            limiter.reserve(now=1122)
        limiter.reserve(now=90000)
        with self.assertRaises(QuotaExceeded):
            limiter.reserve(now=180000)

    def test_clock_rollback_does_not_reset_window(self):
        limiter = RequestLimits(self.path, 1, 10, 10)
        limiter.reserve(now=1000)
        for now in (0, 500, 999, 1050):
            with self.assertRaises(QuotaExceeded):
                limiter.reserve(now=now)

    def test_failed_attempt_remains_charged(self):
        limiter = RequestLimits(self.path, 1, 10, 10)
        limiter.reserve(now=1000)
        # A provider exception after admission does not undo the reservation.
        with self.assertRaises(QuotaExceeded):
            limiter.reserve(now=1001)

    def test_threads_share_one_atomic_limit(self):
        limiter = RequestLimits(self.path, 3, 10, 10)

        def attempt(_):
            try:
                limiter.reserve(now=1000)
                return True
            except QuotaExceeded:
                return False

        with ThreadPoolExecutor(max_workers=12) as pool:
            self.assertEqual(sum(pool.map(attempt, range(30))), 3)

    def test_processes_share_one_atomic_limit(self):
        ctx = multiprocessing.get_context("spawn")
        queue = ctx.Queue()
        processes = [ctx.Process(target=_reserve_in_process, args=(self.path, queue)) for _ in range(6)]
        for process in processes:
            process.start()
        for process in processes:
            process.join(15)
            self.assertEqual(process.exitcode, 0)
        self.assertEqual(sum(queue.get(timeout=2) for _ in processes), 3)
        queue.close()

    def test_invalid_configuration_and_time_fail_closed(self):
        for path in (":memory:", "relative.sqlite3", ""):
            with self.assertRaises(ValueError):
                RequestLimits(path, 1, 2, 3)
        for value in (0, -1, True, 1.1, "5"):
            with self.assertRaises(ValueError):
                RequestLimits(self.path, value, 2, 3)
        limiter = RequestLimits(self.path, 1, 2, 3)
        for now in (float("nan"), float("inf"), -1, True):
            with self.assertRaises(ValueError):
                limiter.reserve(now=now)

    def test_corrupt_database_does_not_reset_budget(self):
        Path(self.path).write_text("corrupt")
        with self.assertRaises(Exception):
            RequestLimits(self.path, 1, 2, 3)
        self.assertEqual(Path(self.path).read_text(), "corrupt")


if __name__ == "__main__":
    unittest.main()
