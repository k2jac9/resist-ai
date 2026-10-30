"""Shared execution/export path for legacy UI runs. No silent fixture fallback."""
from __future__ import annotations

import logging
import math
from typing import Any

from src.research_integrity import error_document, report_document

logger = logging.getLogger(__name__)

PATHOGEN_LABELS = {
    "Acinetobacter baumannii": "acinetobacter_baumannii",
    "Staphylococcus aureus (MRSA)": "staphylococcus_aureus",
    "Klebsiella pneumoniae": "klebsiella_pneumoniae",
    "Pseudomonas aeruginosa": "pseudomonas_aeruginosa",
}


def _pathogen_key(label: str) -> str:
    if not isinstance(label, str) or label not in PATHOGEN_LABELS:
        raise ValueError("invalid_input")
    return PATHOGEN_LABELS[label]


def _demo_inputs(key: str, n: int) -> dict[str, Any]:
    from src.ui.common import get_demo_targets, _demo_candidates_to_display
    return {"pathogen": key, "targets": get_demo_targets(key),
            "candidates": _demo_candidates_to_display(key, n),
            "metadata": {"demo_mode": True, "source": "explicit_simulation",
                         "compound_and_target_identity_verified": False}}


def _run_legacy(key: str, n: int) -> dict[str, Any]:
    from src.ui.common import get_orch
    orchestrator = get_orch()
    if orchestrator is None:
        raise LookupError("pipeline_unavailable")
    return orchestrator.run_full_pipeline(key, n, demo_mode=False, generate_novel=True).to_dict()


def execute_report(label: str, max_n: int, demo: bool) -> tuple[str, str]:
    """Return rendered report plus JSON, or a redacted failure with no fake data."""
    try:
        if type(demo) is not bool or isinstance(max_n, bool) or not isinstance(max_n, (int, float)):
            return error_document("invalid_input")
        if not math.isfinite(max_n) or not 1 <= max_n <= 10 or int(max_n) != max_n:
            return error_document("invalid_input")
        key = _pathogen_key(label)
    except (ValueError, TypeError, KeyError):
        return error_document("invalid_input")
    try:
        data = _demo_inputs(key, int(max_n)) if demo else _run_legacy(key, int(max_n))
    except LookupError:
        return error_document("pipeline_unavailable")
    except Exception as exc:
        # Provider errors can contain request bodies, credentials, or private context.
        logger.warning("Research execution failed (%s)", type(exc).__name__)
        return error_document("pipeline_failed")
    try:
        return report_document(data, simulated=demo)
    except (ValueError, TypeError):
        return error_document("invalid_result")
