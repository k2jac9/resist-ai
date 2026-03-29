"""ResistAI SDK -- composable drug-discovery pipeline.

Quick start::

    from src.sdk import Pipeline, Target

    target = Target.from_sequence("MELPNIMH...", name="NDM-1")
    results = Pipeline(target).fold().screen().dock(top_k=3).run(progress=True)
    print(results.to_report())
"""

from src.sdk.batch import BatchResults, BatchRunner, ComparisonReport
from src.sdk.pipeline import Pipeline
from src.sdk.results import (
    BinderDesign,
    DockingPose,
    NovelMolecule,
    PipelineResults,
    ScreeningHit,
    ValidationResult,
)
from src.sdk.target import Target
from src.sdk.webhooks import WebhookConfig, WebhookManager, slack_webhook

__all__ = [
    "Pipeline",
    "Target",
    "PipelineResults",
    "ScreeningHit",
    "DockingPose",
    "NovelMolecule",
    "BinderDesign",
    "ValidationResult",
    "WebhookConfig",
    "WebhookManager",
    "slack_webhook",
    "BatchRunner",
    "BatchResults",
    "ComparisonReport",
]
