"""Molecule Comparison Module.

Compare drug candidates across multiple dimensions with radar charts,
ranked tables, and summary statistics.
"""
from __future__ import annotations

from typing import Any

try:
    import plotly.graph_objects as go
except ImportError:
    go = None  # type: ignore[assignment]

try:
    import pandas as pd
except ImportError:
    pd = None  # type: ignore[assignment]

# Spectrum palette matching the app dark theme
_COLORS = [
    "#00C4B4",  # teal (primary)
    "#7C8CF8",  # soft blue
    "#F43F5E",  # rose
    "#F59E0B",  # amber
    "#FB923C",  # orange
    "#94A3B8",  # slate
    "#E2E8F0",  # off-white
    "#1E2D4A",  # blue-grey
]

_BG = "#0A0F1E"

# Dimensions available for comparison and ranking
DIMENSIONS = ["Binding", "Safety", "Overall", "Druggability", "Selectivity"]


def _parse_pct(value: str | float) -> float:
    """Convert a percentage string like '87%' or float to 0-1 float."""
    if isinstance(value, (int, float)):
        return float(value) if value <= 1.0 else value / 100.0
    s = str(value).strip().rstrip("%")
    try:
        v = float(s)
        return v / 100.0 if v > 1.0 else v
    except (ValueError, TypeError):
        return 0.0


def _ensure_dimensions(candidate: dict) -> dict:
    """Ensure candidate has all dimensions, synthesising missing ones."""
    c = dict(candidate)
    binding = _parse_pct(c.get("binding", c.get("Binding", 0)))
    safety = _parse_pct(c.get("safety", c.get("Safety", 0)))
    overall = _parse_pct(c.get("overall", c.get("Overall", 0)))

    c.setdefault("Binding", binding)
    c.setdefault("Safety", safety)
    c.setdefault("Overall", overall)
    # Derive druggability and selectivity from available data
    c.setdefault("Druggability", round(0.6 * binding + 0.4 * safety, 3))
    c.setdefault("Selectivity", round(0.4 * binding + 0.6 * (1.0 - abs(binding - safety)), 3))
    return c


def compare_candidates(candidates: list[dict]) -> dict:
    """Compare multiple drug candidates on all dimensions.

    Each candidate dict has: name, smiles, binding, safety, overall, moa, phase.
    Returns comparison data with rankings per dimension.
    """
    enriched = [_ensure_dimensions(c) for c in candidates]
    rankings: dict[str, list[dict]] = {}
    for dim in DIMENSIONS:
        rankings[dim] = rank_by_dimension(enriched, dim)

    best_per_dim = {
        dim: ranked[0]["name"] if ranked else "N/A"
        for dim, ranked in rankings.items()
    }

    return {
        "candidates": enriched,
        "rankings": rankings,
        "best_per_dimension": best_per_dim,
        "dimensions": DIMENSIONS,
        "count": len(enriched),
    }


def generate_radar_chart(candidates: list[dict]) -> Any:
    """Create a Plotly radar chart comparing candidates.

    Axes: Binding, Safety, Overall, Druggability, Selectivity.
    One trace per candidate, overlaid.
    Dark theme matching the app (#0A0F1E bg, teal accent).
    """
    if go is None:
        return None

    enriched = [_ensure_dimensions(c) for c in candidates]
    axes = DIMENSIONS
    fig = go.Figure()

    for i, cand in enumerate(enriched):
        name = cand.get("name", cand.get("💊 Drug", f"Candidate {i + 1}"))
        values = [_parse_pct(cand.get(dim, 0)) for dim in axes]
        # Close the polygon
        values_closed = values + [values[0]]
        axes_closed = axes + [axes[0]]
        color = _COLORS[i % len(_COLORS)]

        fig.add_trace(go.Scatterpolar(
            r=values_closed,
            theta=axes_closed,
            fill="toself",
            fillcolor=color.replace(")", ",0.10)").replace("rgb", "rgba")
            if "rgb" in color else f"rgba({int(color[1:3], 16)},{int(color[3:5], 16)},{int(color[5:7], 16)},0.10)",
            line=dict(color=color, width=2),
            name=name,
        ))

    fig.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(
                visible=True, range=[0, 1], gridcolor="#1E2D4A",
                tickvals=[0.25, 0.5, 0.75, 1.0],
                ticktext=["25%", "50%", "75%", "100%"],
            ),
            angularaxis=dict(gridcolor="#1E2D4A"),
        ),
        paper_bgcolor=_BG,
        plot_bgcolor=_BG,
        font=dict(color="#E2E8F0", size=12),
        legend=dict(
            font=dict(size=11, color="#E2E8F0"),
            bgcolor="rgba(0,0,0,0.3)",
            bordercolor="#1E2D4A",
            borderwidth=1,
        ),
        margin=dict(l=80, r=80, t=60, b=60),
        title=dict(
            text="Drug Candidate Comparison",
            font=dict(color="#00C4B4", size=16),
        ),
    )
    return fig


def generate_comparison_table(candidates: list[dict]) -> Any:
    """Build a comparison table as a list-of-dicts (for gr.Dataframe).

    Returns a pandas DataFrame if available, else a list of dicts.
    """
    enriched = [_ensure_dimensions(c) for c in candidates]
    rows = []
    for i, c in enumerate(enriched):
        name = c.get("name", c.get("💊 Drug", f"Candidate {i + 1}"))
        rows.append({
            "Rank": i + 1,
            "Drug": name,
            "Binding": f"{_parse_pct(c.get('Binding', 0)):.0%}",
            "Safety": f"{_parse_pct(c.get('Safety', 0)):.0%}",
            "Overall": f"{_parse_pct(c.get('Overall', 0)):.0%}",
            "Druggability": f"{_parse_pct(c.get('Druggability', 0)):.0%}",
            "Selectivity": f"{_parse_pct(c.get('Selectivity', 0)):.0%}",
            "MoA": c.get("moa", c.get("Why It Works", "")),
        })
    if pd is not None:
        return pd.DataFrame(rows)
    return rows


def rank_by_dimension(candidates: list[dict], dimension: str) -> list[dict]:
    """Re-rank candidates by a specific dimension.

    Args:
        candidates: List of candidate dicts (already enriched or raw).
        dimension: One of DIMENSIONS.

    Returns:
        Sorted list of dicts with name, score, and rank.
    """
    enriched = [_ensure_dimensions(c) for c in candidates]
    scored = []
    for c in enriched:
        name = c.get("name", c.get("💊 Drug", "Unknown"))
        score = _parse_pct(c.get(dimension, 0))
        scored.append({"name": name, "score": score, **c})

    scored.sort(key=lambda x: x["score"], reverse=True)
    for i, entry in enumerate(scored, 1):
        entry["rank"] = i
    return scored
