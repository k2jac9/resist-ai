"""Tests for the candidate-comparison utilities."""
import pytest

from src.comparison import (
    DIMENSIONS,
    _ensure_dimensions,
    _parse_pct,
    compare_candidates,
    rank_by_dimension,
)


class TestParsePct:
    @pytest.mark.parametrize("value,expected", [
        ("87%", 0.87),
        (0.5, 0.5),
        (75, 0.75),
        ("0.42", 0.42),
        ("not a number", 0.0),
    ])
    def test_parse(self, value, expected):
        assert _parse_pct(value) == pytest.approx(expected)


class TestEnsureDimensions:
    def test_fills_all_dimensions(self):
        out = _ensure_dimensions({"name": "drugA", "binding": "80%", "safety": "60%"})
        for dim in DIMENSIONS:
            assert dim in out
        assert out["Binding"] == pytest.approx(0.8)
        assert out["Druggability"] == pytest.approx(0.6 * 0.8 + 0.4 * 0.6, abs=1e-3)

    def test_does_not_mutate_input(self):
        original = {"name": "x", "binding": "50%"}
        _ensure_dimensions(original)
        assert "Druggability" not in original


class TestCompareCandidates:
    def _cands(self):
        return [
            {"name": "A", "binding": "90%", "safety": "50%", "overall": "70%"},
            {"name": "B", "binding": "60%", "safety": "95%", "overall": "80%"},
        ]

    def test_structure_and_count(self):
        out = compare_candidates(self._cands())
        assert out["count"] == 2
        assert set(out["rankings"].keys()) == set(DIMENSIONS)
        assert out["best_per_dimension"]["Binding"] == "A"
        assert out["best_per_dimension"]["Safety"] == "B"

    def test_empty_input(self):
        out = compare_candidates([])
        assert out["count"] == 0
        assert out["best_per_dimension"]["Binding"] == "N/A"


class TestRankByDimension:
    def test_sorted_descending_with_rank(self):
        cands = [
            _ensure_dimensions({"name": "lo", "binding": "10%"}),
            _ensure_dimensions({"name": "hi", "binding": "90%"}),
        ]
        ranked = rank_by_dimension(cands, "Binding")
        assert [r["name"] for r in ranked] == ["hi", "lo"]
        assert [r["rank"] for r in ranked] == [1, 2]

    def test_empty(self):
        assert rank_by_dimension([], "Binding") == []
