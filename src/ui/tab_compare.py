"""Tab: Compare Candidates — radar chart and ranking comparison."""
from __future__ import annotations

from src.comparison import (
    compare_candidates as _compare_candidates,
    generate_radar_chart,
    generate_comparison_table,
    rank_by_dimension,
    DIMENSIONS as _CMP_DIMS,
)
from src.ui.common import PATHOGENS, _COMPOUNDS, _mode_badge


def compare_candidates_ui(pathogen_label: str, rank_dim: str = "Overall"):
    """Load demo candidates and generate comparison outputs."""
    from src.ui.common import get_demo_candidates
    pathogen_key = PATHOGENS.get(pathogen_label, {}).get("key", "acinetobacter_baumannii")
    raw = get_demo_candidates(pathogen_key, min(5, len(_COMPOUNDS)))
    enriched = []
    for c in raw:
        enriched.append({
            "name": c["drug_name"],
            "Binding": c["binding"],
            "Safety": c["safety"],
            "Overall": c["overall"],
            "moa": c.get("why", ""),
        })
    # Get best-per-dimension from unranked data (avoids mutation bug)
    comparison = _compare_candidates(enriched)
    # Then rank for display
    if rank_dim and rank_dim in _CMP_DIMS:
        enriched = rank_by_dimension(enriched, rank_dim)
    fig = generate_radar_chart(enriched)
    table = generate_comparison_table(enriched)
    info = PATHOGENS.get(pathogen_label, {})
    best = comparison.get("best_per_dimension", {})
    summary = (
        f"{_mode_badge(True)}\n\n"
        f"### Comparison: {pathogen_label} {info.get('icon', '')}\n\n"
        f"**{len(enriched)} candidates** compared across {len(_CMP_DIMS)} dimensions "
        f"(ranked by **{rank_dim}**).\n\n"
        f"| Dimension | Best Candidate |\n|-----------|----------------|\n"
        + "\n".join(f"| {dim} | {name} |" for dim, name in best.items())
        + "\n"
    )
    return fig, table, summary


def rerank_candidates_ui(pathogen_label: str, rank_dim: str):
    """Re-rank when the dimension dropdown changes."""
    return compare_candidates_ui(pathogen_label, rank_dim)
