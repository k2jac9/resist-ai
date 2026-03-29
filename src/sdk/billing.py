"""Cost estimation and usage metering for NVIDIA NIM API calls."""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class CostEstimator:
    """Estimates and tracks API usage costs per model call."""

    COST_PER_CALL: dict[str, float] = field(default_factory=lambda: {
        "esmfold": 0.002,
        "evo2": 0.005,
        "boltz2": 0.01,
        "diffdock": 0.008,
        "molmim": 0.003,
        "rfdiffusion": 0.015,
        "proteinmpnn": 0.005,
        "nebius_llm": 0.002,
    })

    _usage: list[dict] = field(default_factory=list)

    # Traditional drug discovery benchmarks
    _TRADITIONAL_COST: float = 2.6e9  # $2.6B
    _TRADITIONAL_YEARS: int = 12      # average 10-15 years

    def log_call(
        self, model: str, elapsed_ms: float = 0, metadata: dict | None = None
    ) -> dict:
        """Record a model call with timestamp, cost, and duration."""
        model_key = model.lower().replace("-", "")
        cost = self.COST_PER_CALL.get(model_key, 0.0)
        entry = {
            "model": model_key,
            "cost": cost,
            "elapsed_ms": elapsed_ms,
            "timestamp": time.time(),
            "metadata": metadata or {},
        }
        self._usage.append(entry)
        return entry

    def estimate_pipeline_cost(self, steps: list[str]) -> dict:
        """Estimate total cost for a sequence of model steps."""
        breakdown: dict[str, float] = {}
        for step in steps:
            key = step.lower().replace("-", "")
            cost = self.COST_PER_CALL.get(key, 0.0)
            breakdown[key] = breakdown.get(key, 0.0) + cost
        total = sum(breakdown.values())
        ratio = self._TRADITIONAL_COST / total if total > 0 else float("inf")
        return {
            "total": round(total, 4),
            "breakdown": breakdown,
            "vs_traditional": f"{ratio:,.0f}x cheaper",
        }

    def get_session_cost(self) -> dict:
        """Return total cost and call count for the current session."""
        total = sum(e["cost"] for e in self._usage)
        by_model: dict[str, dict] = {}
        for entry in self._usage:
            m = entry["model"]
            if m not in by_model:
                by_model[m] = {"calls": 0, "cost": 0.0, "total_ms": 0.0}
            by_model[m]["calls"] += 1
            by_model[m]["cost"] = round(by_model[m]["cost"] + entry["cost"], 6)
            by_model[m]["total_ms"] += entry["elapsed_ms"]
        return {
            "total_cost": round(total, 6),
            "total_calls": len(self._usage),
            "by_model": by_model,
        }

    def get_roi_comparison(self) -> dict:
        """Compare AI pipeline cost vs traditional drug discovery."""
        session = self.get_session_cost()
        ai_cost = session["total_cost"]
        full_screen_est = ai_cost * 1000 if ai_cost > 0 else 0.05
        return {
            "traditional": {
                "cost": f"${self._TRADITIONAL_COST:,.0f}",
                "timeline": f"{self._TRADITIONAL_YEARS} years",
            },
            "ai_pipeline": {
                "cost_per_run": f"${ai_cost:.4f}",
                "est_full_screen": f"${full_screen_est:,.2f}",
                "timeline": "hours to days",
            },
            "savings_factor": (
                f"{self._TRADITIONAL_COST / full_screen_est:,.0f}x"
                if full_screen_est > 0
                else "N/A"
            ),
            "time_reduction": f"{self._TRADITIONAL_YEARS * 365}x (days vs years)",
        }

    def format_cost_report(self) -> str:
        """Return a formatted markdown report of costs and ROI."""
        session = self.get_session_cost()
        roi = self.get_roi_comparison()
        lines = [
            "# Cost & Usage Report",
            "",
            f"**Total calls:** {session['total_calls']}  ",
            f"**Total cost:** ${session['total_cost']:.4f}",
            "",
            "## Breakdown by Model",
            "",
            "| Model | Calls | Cost | Avg Latency |",
            "|-------|------:|-----:|------------:|",
        ]
        for model, stats in session["by_model"].items():
            avg_ms = stats["total_ms"] / stats["calls"] if stats["calls"] else 0
            lines.append(
                f"| {model} | {stats['calls']} | ${stats['cost']:.4f} | {avg_ms:.0f}ms |"
            )
        lines += [
            "",
            "## ROI vs Traditional Drug Discovery",
            "",
            f"- Traditional: {roi['traditional']['cost']} over {roi['traditional']['timeline']}",
            f"- AI per run: {roi['ai_pipeline']['cost_per_run']}",
            f"- Full screen estimate: {roi['ai_pipeline']['est_full_screen']}",
            f"- **Savings: {roi['savings_factor']}**",
            f"- **Speed: {roi['time_reduction']}**",
        ]
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Return serializable dict of all usage data."""
        return {
            "usage": list(self._usage),
            "session": self.get_session_cost(),
            "roi": self.get_roi_comparison(),
            "cost_table": dict(self.COST_PER_CALL),
        }


@dataclass
class PricingTier:
    """SaaS pricing tiers for the drug discovery platform."""

    TIERS: dict[str, dict] = field(default_factory=lambda: {
        "free": {
            "monthly_runs": 5,
            "price": 0,
            "models": ["esmfold", "molmim"],
        },
        "starter": {
            "monthly_runs": 100,
            "price": 99,
            "models": "all",
        },
        "pro": {
            "monthly_runs": 1000,
            "price": 499,
            "models": "all",
            "priority": True,
        },
        "enterprise": {
            "monthly_runs": "unlimited",
            "price": "custom",
            "models": "all",
            "sla": True,
        },
    })

    def recommend_tier(self, monthly_runs: int) -> str:
        """Recommend the most cost-effective tier for a given run count."""
        if monthly_runs <= 5:
            return "free"
        if monthly_runs <= 100:
            return "starter"
        if monthly_runs <= 1000:
            return "pro"
        return "enterprise"

    def get_tier(self, name: str) -> dict | None:
        """Return tier details by name."""
        return self.TIERS.get(name.lower())

    def format_pricing_table(self) -> str:
        """Return a markdown pricing table."""
        lines = [
            "# Pricing Tiers",
            "",
            "| Tier | Monthly Runs | Price | Models | Extras |",
            "|------|------------:|------:|--------|--------|",
        ]
        for name, t in self.TIERS.items():
            runs = t["monthly_runs"]
            price = f"${t['price']}" if isinstance(t["price"], int) else t["price"]
            models = ", ".join(t["models"]) if isinstance(t["models"], list) else t["models"]
            extras = []
            if t.get("priority"):
                extras.append("priority queue")
            if t.get("sla"):
                extras.append("SLA")
            lines.append(
                f"| {name.capitalize()} | {runs} | {price} | {models} | {', '.join(extras) or '-'} |"
            )
        return "\n".join(lines)
