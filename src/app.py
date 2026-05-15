"""AMR-AI: Gradio Web Application for AI Drug Discovery.

Dual-audience design using progressive disclosure:
- Surface layer: plain-language for executives, judges, clinicians
- Expandable sections: technical details for scientists and engineers

This is the thin entry-point shell. All tab logic lives in src/ui/*.
"""
from __future__ import annotations

import logging
import os

from src.ui import create_app
from src.ui.common import _CSS

# ---------------------------------------------------------------------------
# Re-export key symbols so existing imports from src.app keep working
# ---------------------------------------------------------------------------
from src.ui.common import (          # noqa: F401  — backwards compat
    PATHOGENS,
    _COMPOUNDS,
    TARGET_DETAILS,
    _EXAMPLE_TARGETS,
    _EXAMPLE_DRUGS_SAFETY,
    _rr,
    _to_df,
    _mode_badge,
    _source_tag,
    _explain_score,
)
from src.ui.tab_problem import (     # noqa: F401
    _PROBLEM_MD,
    _pathogen_cards,
)
from src.ui.tab_pipeline import (    # noqa: F401
    _PIPELINE_INTRO,
    run_pipeline_ui,
    _build_targets,
    _build_candidates,
    _build_tech_detail,
    _generate_summary,
)
from src.ui.tab_models import (      # noqa: F401
    _HOW_IT_WORKS,
    predict_binding,
)
from src.ui.tab_safety import (      # noqa: F401
    _SAFETY_INTRO,
    analyze_safety,
)
from src.ui.tab_viewer import (      # noqa: F401
    fold_and_visualize,
)
from src.ui.tab_compare import (     # noqa: F401
    compare_candidates_ui,
    rerank_candidates_ui,
)
from src.ui.tab_report import (      # noqa: F401
    generate_report,
)
from src.ui.tab_regulatory import (  # noqa: F401
    create_regulatory_tab,
)
from src.comparison import DIMENSIONS as _CMP_DIMS  # noqa: F401

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    ui_user = os.environ.get("RESISTAI_UI_USER")
    ui_pass = os.environ.get("RESISTAI_UI_PASSWORD")
    auth = (ui_user, ui_pass) if ui_user and ui_pass else None
    if auth is None:
        logger.warning(
            "RESISTAI_UI_USER/RESISTAI_UI_PASSWORD not set -- the Gradio UI is "
            "launching WITHOUT authentication. Set both to enable access control."
        )
    create_app().launch(
        # Host is configurable; default 0.0.0.0 preserves container reachability.
        server_name=os.environ.get("RESISTAI_UI_HOST", "0.0.0.0"),
        server_port=int(os.environ.get("RESISTAI_UI_PORT", "7860")),
        share=False,
        show_error=False,
        auth=auth,
        css=_CSS,
    )


if __name__ == "__main__":
    main()
