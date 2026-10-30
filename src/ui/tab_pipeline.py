"""Legacy pipeline display with explicit simulation and evidence limitations."""
from __future__ import annotations

import json

from src.research_execution import execute_report
from src.research_integrity import LIMITATION

_PIPELINE_INTRO = """
### Research pipeline records

Simulation is explicit and does not call a model. Non-simulated execution invokes the
legacy orchestrator, which still contains unverified target/compound data and heuristic
scoring. Its output is marked **unverified**, not certified live scientific evidence.
Use the Evidence Review tab for a bounded, separately receipted Nebius request.
"""


def run_pipeline_ui(label: str, max_n: int, demo: bool, progress=None):
    summary, exported = execute_report(label, max_n, demo)
    record = json.loads(exported)
    if record["status"] == "failed":
        return f"Run failed: {record['error']}", None, None, summary
    raw = record["raw_results"]
    targets = raw.get("targets", [])
    candidates = raw.get("top_candidates", raw.get("candidates", []))
    target_rows = [{"Target label (unverified)": t.get("name", t.get("🎯 Target", ""))}
                   for t in targets if isinstance(t, dict)]
    candidate_rows = [{"Compound label (unverified)": c.get("drug_name", c.get("💊 Drug", "")),
                       "Evidence status": record["evidence_status"]}
                      for c in candidates if isinstance(c, dict)]
    import pandas as pd
    status = ("SIMULATED result recorded. No provider inference occurred." if record["evidence_status"] == "simulated"
              else "Legacy execution recorded. Scientific data and model provenance remain unverified.")
    return status, pd.DataFrame(target_rows), pd.DataFrame(candidate_rows), summary


# Preserve the import surface used by src.app; these helpers describe fixtures only.
def _build_targets(key: str) -> list[dict]:
    from src.ui.common import get_demo_targets
    return get_demo_targets(key)


def _build_candidates(n: int, pathogen_key: str = "acinetobacter_baumannii") -> list[dict]:
    from src.ui.common import _demo_candidates_to_display
    return _demo_candidates_to_display(pathogen_key, n)


def _build_tech_detail(key: str, targets: list, candidates: list) -> list[str]:
    return ["### Explicit simulation", "Fixture values are not measured model predictions.", LIMITATION]


def _generate_summary(label: str, targets: list, candidates: list, tech_lines: list) -> str:
    return f"Recorded {len(targets)} target entries and {len(candidates)} candidate entries.\n\n{LIMITATION}"
