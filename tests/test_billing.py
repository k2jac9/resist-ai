"""Tests for cost estimation and pricing-tier helpers."""
import json

import pytest

from src.sdk.billing import CostEstimator, PricingTier


class TestCostEstimator:
    def test_log_call_normalises_model_key(self):
        est = CostEstimator()
        entry = est.log_call("Boltz-2", elapsed_ms=120)
        assert entry["model"] == "boltz2"
        assert entry["cost"] == pytest.approx(0.01)
        assert len(est._usage) == 1

    def test_unknown_model_costs_zero(self):
        est = CostEstimator()
        assert est.log_call("mystery-model")["cost"] == 0.0

    def test_estimate_pipeline_cost_sums_breakdown(self):
        est = CostEstimator()
        out = est.estimate_pipeline_cost(["esmfold", "boltz2", "boltz2"])
        assert out["breakdown"]["boltz2"] == pytest.approx(0.02)
        assert out["total"] == pytest.approx(0.022)
        assert "cheaper" in out["vs_traditional"]

    def test_estimate_pipeline_cost_zero_is_infinite_cheaper(self):
        out = CostEstimator().estimate_pipeline_cost([])
        assert out["total"] == 0
        assert "inf" in out["vs_traditional"]

    def test_session_cost_groups_by_model(self):
        est = CostEstimator()
        est.log_call("boltz2", elapsed_ms=100)
        est.log_call("boltz2", elapsed_ms=200)
        est.log_call("molmim", elapsed_ms=50)
        session = est.get_session_cost()
        assert session["total_calls"] == 3
        assert session["by_model"]["boltz2"]["calls"] == 2
        assert session["by_model"]["boltz2"]["total_ms"] == 300
        assert session["total_cost"] == pytest.approx(0.023)

    def test_to_dict_is_json_serializable(self):
        est = CostEstimator()
        est.log_call("evo2")
        json.dumps(est.to_dict())  # must not raise

    def test_format_cost_report_is_markdown(self):
        est = CostEstimator()
        est.log_call("boltz2", elapsed_ms=100)
        report = est.format_cost_report()
        assert "# Cost & Usage Report" in report
        assert "boltz2" in report


class TestPricingTier:
    @pytest.mark.parametrize("runs,expected", [
        (0, "free"), (5, "free"), (6, "starter"), (100, "starter"),
        (101, "pro"), (1000, "pro"), (1001, "enterprise"), (99999, "enterprise"),
    ])
    def test_recommend_tier(self, runs, expected):
        assert PricingTier().recommend_tier(runs) == expected

    def test_get_tier_case_insensitive(self):
        pt = PricingTier()
        assert pt.get_tier("PRO")["price"] == 499
        assert pt.get_tier("nope") is None

    def test_format_pricing_table(self):
        table = PricingTier().format_pricing_table()
        assert "# Pricing Tiers" in table
        assert "Enterprise" in table
        assert "SLA" in table
