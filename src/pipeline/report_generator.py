"""Report generator for AMR-AI pipeline results.

Produces markdown summaries, candidate tables, regulatory outlines,
and exports structured JSON plus human-readable reports.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

from ..models.schemas import DrugCandidate, PipelineResults

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generates formatted reports from pipeline results."""

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def generate_summary(self, results: PipelineResults) -> str:
        """Produce a markdown summary of pipeline findings."""
        meta = results.metadata
        duration = meta.get("duration_seconds", "N/A")
        screened = meta.get("compounds_screened", 0)
        demo = meta.get("demo_mode", True)
        mode_label = "Demo Mode" if demo else "Production"

        lines = [
            f"# AMR-AI Pipeline Report",
            "",
            f"**Pathogen:** {results.pathogen}  ",
            f"**Timestamp:** {meta.get('timestamp', 'N/A')}  ",
            f"**Duration:** {duration}s  ",
            f"**Mode:** {mode_label}  ",
            "",
            "## Stage 1: Target Discovery",
            "",
            f"Identified **{len(results.targets)}** druggable targets:",
            "",
        ]
        for t in results.targets:
            lines.append(
                f"- **{t.name}** (PDB: {t.pdb_code}) -- "
                f"{t.function} [druggability: {t.druggability_score:.2f}]"
            )

        lines += [
            "",
            "## Stage 2: Virtual Drug Screening",
            "",
            f"Screened **{screened}** compounds against top target.",
            "",
        ]
        for sr in results.screening_results:
            lines.append(
                f"- **{sr.target_name}**: {len(sr.hits)} hits "
                f"(threshold >= {sr.threshold_used})"
            )

        lines += [
            "",
            "## Stage 3: Safety Prediction",
            "",
            f"Evaluated **{len(results.safety_reports)}** top hits for ADMET and off-target risk.",
            "",
        ]
        flagged = [r for r in results.safety_reports if r.flags]
        if flagged:
            lines.append(f"**{len(flagged)}** compounds flagged for safety concerns:")
            for r in flagged:
                lines.append(f"- {r.drug_name}: {', '.join(r.flags)}")
        else:
            lines.append("No safety flags raised.")

        lines += [
            "",
            "## Top Candidates",
            "",
            self.generate_candidate_table(results.top_candidates),
        ]
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Candidate table
    # ------------------------------------------------------------------

    def generate_candidate_table(self, candidates: list[DrugCandidate]) -> str:
        """Format candidates as a markdown table."""
        if not candidates:
            return "_No candidates._"

        header = (
            "| Rank | Drug | Target | Binding | Safety | "
            "Overall | Pathway | Confidence |"
        )
        sep = (
            "|------|------|--------|---------|--------|"
            "---------|---------|------------|"
        )
        rows = [header, sep]
        for c in candidates:
            rows.append(
                f"| {c.rank} | {c.drug_name} | {c.target_name} | "
                f"{c.binding_affinity:.3f} | {c.safety_score:.2f} | "
                f"**{c.overall_score:.3f}** | {c.regulatory_pathway} | "
                f"{c.confidence:.2f} |"
            )
        return "\n".join(rows)

    # ------------------------------------------------------------------
    # Regulatory outline
    # ------------------------------------------------------------------

    def generate_regulatory_outline(
        self, candidates: list[DrugCandidate]
    ) -> str:
        """Generate a regulatory pathway text for top candidates."""
        lines = [
            "# Regulatory Pathway Outline",
            "",
            "## Applicable Frameworks",
            "",
            "### FDA Modernization Act 2.0 (2022)",
            "",
            "The FDA Modernization Act 2.0 eliminates the requirement that drugs "
            "must be tested on animals before human clinical trials, enabling the "
            "use of **New Approach Methodologies (NAMs)** including:",
            "",
            "- Organ-on-chip models",
            "- Computational (in silico) modeling",
            "- Bioprinted tissue models",
            "- Microphysiological systems",
            "",
            "This pipeline's AI-driven predictions align with Section 2(a) of the "
            "Act, which permits alternative test methods to support IND applications.",
            "",
            "### 505(b)(2) Pathway for Repurposed Drugs",
            "",
            "Candidates with prior FDA approval history may leverage the 505(b)(2) "
            "pathway, which allows applicants to rely on existing safety and efficacy "
            "data.  Benefits include:",
            "",
            "- Reduced preclinical requirements",
            "- Shorter development timelines (3-5 years vs. 10+ years)",
            "- Lower development costs",
            "- Established safety profiles from prior use",
            "",
        ]

        repurposed = [c for c in candidates if c.regulatory_pathway == "505(b)(2)"]
        if repurposed:
            lines.append("**Candidates eligible for 505(b)(2):**")
            lines.append("")
            for c in repurposed:
                lines.append(f"- {c.drug_name} (rank #{c.rank})")
            lines.append("")

        lines += [
            "### New Approach Methodologies (NAMs) Framework",
            "",
            "The NAMs framework supports regulatory acceptance of non-animal "
            "testing data.  This pipeline contributes evidence through:",
            "",
            "- **In silico target identification** -- AI-driven target discovery "
            "using genomic and structural data",
            "- **Computational docking** -- Virtual screening replaces initial "
            "animal-based SAR studies",
            "- **Predictive ADMET modeling** -- Machine learning toxicity "
            "predictions reduce animal testing needs",
            "- **Off-target prediction** -- Computational safety profiling before "
            "any in vivo work",
            "",
            "### Health Canada GMLP Alignment",
            "",
            "The **Good Machine Learning Practice (GMLP)** principles published "
            "jointly by Health Canada, the FDA, and the UK MHRA provide a "
            "governance framework for AI/ML in drug development:",
            "",
            "1. Multi-disciplinary expertise informs the full ML lifecycle",
            "2. Good software engineering and security practices are applied",
            "3. Clinical study participants represent the intended patient population",
            "4. Training data are independent of test data",
            "5. Reference datasets are based on best available methods",
            "6. Model design is suited to the available data and task",
            "7. Focus is on the performance of the human-AI team",
            "8. Testing demonstrates real-world performance",
            "9. Users are provided clear, context-relevant information",
            "10. Deployed models are monitored and managed for re-training triggers",
            "",
            "This pipeline is designed to conform with principles 1-6 and 9-10 "
            "at the current development stage.",
        ]
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_results(
        self,
        results: PipelineResults,
        output_dir: str,
    ) -> str:
        """Save JSON data and markdown report to *output_dir*.

        Returns:
            Path to the generated markdown report file.
        """
        os.makedirs(output_dir, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")

        # JSON export
        json_path = os.path.join(output_dir, f"results_{ts}.json")
        with open(json_path, "w") as fh:
            json.dump(results.to_dict(), fh, indent=2)
        logger.info("Exported JSON results to %s", json_path)

        # Markdown report
        md_content = self.generate_summary(results)
        md_content += "\n\n---\n\n"
        md_content += self.generate_regulatory_outline(results.top_candidates)

        md_path = os.path.join(output_dir, f"report_{ts}.md")
        with open(md_path, "w") as fh:
            fh.write(md_content)
        logger.info("Exported markdown report to %s", md_path)

        return md_path
