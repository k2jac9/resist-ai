"""ResistAI research UI entry point. Bind privately unless UI auth is configured."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from src.ui import create_app
from src.ui_security import launch_options
from src.ui.common import (  # noqa: F401
    PATHOGENS, _COMPOUNDS, TARGET_DETAILS, _EXAMPLE_TARGETS,
    _EXAMPLE_DRUGS_SAFETY, _rr, _to_df, _mode_badge, _source_tag,
    _explain_score, _CSS,
)
from src.ui.tab_problem import _PROBLEM_MD, _pathogen_cards  # noqa: F401
from src.ui.tab_pipeline import (  # noqa: F401
    _PIPELINE_INTRO, run_pipeline_ui, _build_targets, _build_candidates,
    _build_tech_detail, _generate_summary,
)
from src.ui.tab_models import _HOW_IT_WORKS, predict_binding  # noqa: F401
from src.ui.tab_safety import _SAFETY_INTRO, analyze_safety  # noqa: F401
from src.ui.tab_viewer import fold_and_visualize  # noqa: F401
from src.ui.tab_compare import compare_candidates_ui, rerank_candidates_ui  # noqa: F401
from src.ui.tab_report import generate_report  # noqa: F401
from src.ui.tab_regulatory import create_regulatory_tab  # noqa: F401
from src.comparison import DIMENSIONS as _CMP_DIMS  # noqa: F401


def main() -> None:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
    os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")
    create_app().launch(css=_CSS, **launch_options())


if __name__ == "__main__":
    main()
