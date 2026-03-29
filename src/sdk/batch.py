"""Batch pipeline runner -- run drug discovery across multiple pathogens.

Executes the full AMR-AI pipeline for each pathogen concurrently using
ThreadPoolExecutor, then cross-compares to find broad-spectrum candidates.

Usage::

    from src.sdk.batch import BatchRunner
    runner = BatchRunner(max_workers=4, max_drugs=5)
    results = runner.run_all_pathogens(demo_mode=True)
    print(results.summary())
"""
from __future__ import annotations

import json
import logging
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from src.models.schemas import DrugCandidate, PipelineResults
from src.pipeline.orchestrator import PipelineOrchestrator

logger = logging.getLogger(__name__)
ProgressCallback = Optional[Callable[[str, str, float], None]]

ALL_PATHOGENS: list[str] = [
    "acinetobacter_baumannii",
    "staphylococcus_aureus",
    "klebsiella_pneumoniae",
    "pseudomonas_aeruginosa",
]


@dataclass
class ComparisonReport:
    """Cross-pathogen comparison of drug candidates."""

    all_candidates: dict[str, list[DrugCandidate]] = field(default_factory=dict)

    def broad_spectrum_candidates(self, min_pathogens: int = 2) -> list[dict]:
        """Drugs that scored well against multiple pathogens."""
        drug_hits: dict[str, list[dict]] = defaultdict(list)
        for pathogen, candidates in self.all_candidates.items():
            for c in candidates:
                drug_hits[c.drug_name].append({
                    "pathogen": pathogen, "overall_score": c.overall_score,
                    "binding_affinity": c.binding_affinity,
                    "safety_score": c.safety_score, "target": c.target_name,
                })
        broad = []
        for drug_name, hits in drug_hits.items():
            if len(hits) >= min_pathogens:
                avg = sum(h["overall_score"] for h in hits) / len(hits)
                broad.append({
                    "drug_name": drug_name, "num_pathogens": len(hits),
                    "avg_overall_score": round(avg, 4),
                    "details": sorted(hits, key=lambda h: h["overall_score"], reverse=True),
                })
        broad.sort(key=lambda d: (d["num_pathogens"], d["avg_overall_score"]), reverse=True)
        return broad

    def best_per_pathogen(self) -> dict[str, dict]:
        """Top candidate per pathogen."""
        best: dict[str, dict] = {}
        for pathogen, candidates in self.all_candidates.items():
            if candidates:
                top = candidates[0]
                best[pathogen] = {
                    "drug_name": top.drug_name, "overall_score": top.overall_score,
                    "binding_affinity": top.binding_affinity,
                    "safety_score": top.safety_score, "target": top.target_name,
                }
        return best

    def format_table(self) -> str:
        """Markdown comparison table."""
        lines = ["## Cross-Pathogen Comparison", ""]
        lines.append("### Best Candidate per Pathogen")
        lines.append("| Pathogen | Drug | Target | Score |")
        lines.append("|----------|------|--------|-------|")
        for pathogen, info in self.best_per_pathogen().items():
            name = pathogen.replace("_", " ").title()
            lines.append(
                f"| {name} | {info['drug_name']} | {info['target']} "
                f"| {info['overall_score']:.3f} |")
        lines.append("")
        broad = self.broad_spectrum_candidates()
        if broad:
            lines.append("### Broad-Spectrum Candidates (active against 2+ pathogens)")
            lines.append("| Drug | Pathogens | Avg Score |")
            lines.append("|------|-----------|-----------|")
            for entry in broad[:10]:
                plist = ", ".join(d["pathogen"].split("_")[0].title() for d in entry["details"])
                lines.append(
                    f"| {entry['drug_name']} | {entry['num_pathogens']} ({plist}) "
                    f"| {entry['avg_overall_score']:.3f} |")
            lines.append("")
        return "\n".join(lines)


@dataclass
class BatchResults:
    """Aggregated results from batch pipeline runs."""

    pathogen_results: dict[str, PipelineResults] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)
    total_duration: float = 0.0

    @property
    def total_targets(self) -> int:
        return sum(len(r.targets) for r in self.pathogen_results.values())

    @property
    def total_candidates(self) -> int:
        return sum(len(r.top_candidates) for r in self.pathogen_results.values())

    @property
    def cross_reactive_drugs(self) -> list[dict]:
        """Drugs effective against 2+ pathogens."""
        return self.compare_results().broad_spectrum_candidates()

    def compare_results(self) -> ComparisonReport:
        """Build a ComparisonReport from all pathogen results."""
        return ComparisonReport(all_candidates={
            p: r.top_candidates for p, r in self.pathogen_results.items()
        })

    def summary(self) -> str:
        """Markdown summary of the batch run."""
        lines = [
            "# Batch Pipeline Results", "",
            f"- **Pathogens analysed:** {len(self.pathogen_results)}",
            f"- **Total targets:** {self.total_targets}",
            f"- **Total candidates:** {self.total_candidates}",
            f"- **Broad-spectrum drugs:** {len(self.cross_reactive_drugs)}",
            f"- **Duration:** {self.total_duration:.1f}s", "",
        ]
        if self.errors:
            lines.append("## Errors")
            for pathogen, err in self.errors.items():
                lines.append(f"- **{pathogen}:** {err}")
            lines.append("")
        for pathogen, result in self.pathogen_results.items():
            name = pathogen.replace("_", " ").title()
            lines.append(f"## {name}")
            lines.append(f"- Targets: {len(result.targets)}, Candidates: {len(result.top_candidates)}")
            for c in result.top_candidates[:3]:
                lines.append(f"  - {c.drug_name} (score={c.overall_score:.3f}, bind={c.binding_affinity:.3f})")
            lines.append("")
        lines.append(self.compare_results().format_table())
        return "\n".join(lines)

    def to_json(self, indent: int = 2) -> str:
        """JSON export of all results."""
        payload: dict[str, Any] = {
            "total_duration": self.total_duration,
            "total_targets": self.total_targets,
            "total_candidates": self.total_candidates,
            "cross_reactive_drugs": self.cross_reactive_drugs,
            "errors": self.errors,
            "pathogens": {p: r.to_dict() for p, r in self.pathogen_results.items()},
        }
        return json.dumps(payload, indent=indent, default=str)


class BatchRunner:
    """Run pipelines across multiple targets/pathogens in parallel."""

    def __init__(self, max_workers: int = 4, max_drugs: int = 5) -> None:
        self._max_workers = max_workers
        self._max_drugs = max_drugs

    def run_all_pathogens(
        self,
        pathogens: list[str] | None = None,
        progress_callback: ProgressCallback = None,
        demo_mode: bool = False,
    ) -> BatchResults:
        """Run the full pipeline for each pathogen in parallel.

        Args:
            pathogens:         Pathogen identifiers, or None for ALL_PATHOGENS.
            progress_callback: ``(pathogen, stage, pct)`` reporter.
            demo_mode:         If True, skip API calls (pure heuristic).
        """
        targets = pathogens or ALL_PATHOGENS
        batch = BatchResults()
        start = time.time()

        def _run_one(pathogen: str) -> tuple[str, PipelineResults]:
            cb = None
            if progress_callback:
                def cb(stage: str, pct: float, msg: str) -> None:
                    progress_callback(pathogen, stage, pct)
            orch = PipelineOrchestrator(progress_callback=cb)
            return pathogen, orch.run_full_pipeline(
                pathogen_name=pathogen, max_drugs=self._max_drugs, demo_mode=demo_mode,
            )

        with ThreadPoolExecutor(max_workers=self._max_workers) as pool:
            futures = {pool.submit(_run_one, p): p for p in targets}
            for future in as_completed(futures):
                pathogen = futures[future]
                try:
                    _, result = future.result()
                    batch.pathogen_results[pathogen] = result
                    logger.info("Completed %s: %d candidates", pathogen, len(result.top_candidates))
                except Exception as exc:
                    batch.errors[pathogen] = str(exc)
                    logger.error("Failed %s: %s", pathogen, exc)

        batch.total_duration = round(time.time() - start, 2)
        return batch

    def run_multi_target(
        self,
        targets: list[dict[str, str]],
        drug_library: list[dict[str, str]],
        demo_mode: bool = False,
    ) -> BatchResults:
        """Screen a drug library against multiple explicit targets.

        Each entry in *targets* should have a ``pathogen`` key.
        """
        pathogens = [t["pathogen"] for t in targets if "pathogen" in t]
        return self.run_all_pathogens(pathogens=pathogens, demo_mode=demo_mode)
