"""Export actual execution records without relabeling fixtures as live results."""
from __future__ import annotations

from src.research_execution import execute_report


def generate_report(label: str, max_n: int, demo: bool) -> tuple[str, str]:
    return execute_report(label, max_n, demo)
