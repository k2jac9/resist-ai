"""Regulatory Intelligence tab for FDA pathway prediction and compliance planning."""

from __future__ import annotations

import json
from typing import Any

import gradio as gr
import pandas as pd
import plotly.graph_objects as go

from ..models.schemas import DrugCandidate
from ..utils.explainability import generate_pipeline_explanations
from ..utils.regulatory import (
    USP_MONOGRAPH_DB,
    calculate_timeline_with_accelerations,
    generate_preind_briefing_document,
    generate_regulatory_report,
    get_usp_monograph_info,
    predict_regulatory_pathway,
)

_REGULATORY_INTRO = """
## 🏛️ Regulatory Intelligence & FDA Pathway Optimizer

Navigate the complex FDA approval landscape with AI-powered regulatory intelligence.
This module helps you:

- 🔍 **Filter drugs by USP monograph** status for accelerated 505(b)(2) pathways
- 📊 **Predict regulatory pathways** with timeline and cost estimates
- 🧠 **Explain AI model predictions** for FDA submissions (2025 guidance compliant)
- 📄 **Generate pre-IND briefing documents** automatically
- ⏱️ **Calculate timelines** with accelerated program benefits (QIDP, Fast Track, Breakthrough)

### Why Monographs Matter

Drugs with **USP-NF monographs** can leverage the **505(b)(2) pathway**, reducing:
- ⏳ Timeline: 3-8 years (vs 10-17 for de novo)
- 💰 Cost: $200-600M (vs $1-2B for de novo)
- 📈 Success rate: 17% (vs 10% for de novo)

For AMR antibiotics, **QIDP designation** adds 5-year market exclusivity + Fast Track + Priority Review.

---
"""


def get_monograph_drugs() -> pd.DataFrame:
    """Get drugs with USP monograph information."""
    data = []
    for drug, info in USP_MONOGRAPH_DB.items():
        data.append({
            "Drug Name": drug,
            "USP Monograph": "✅ Yes" if info["has_monograph"] else "❌ No",
            "Monograph ID": info.get("monograph_id", "N/A"),
            "Category": info.get("category", "N/A"),
            "Generic Available": "✅ Yes" if info.get("generic", False) else "❌ No",
            "Pathway": "505(b)(2)" if info["has_monograph"] and info.get("generic") else "505(b)(1)"
        })

    return pd.DataFrame(data)


def filter_drugs_by_monograph(has_monograph: bool) -> pd.DataFrame:
    """Filter drugs by USP monograph status."""
    df = get_monograph_drugs()
    if has_monograph:
        return df[df["USP Monograph"] == "✅ Yes"]
    else:
        return df[df["USP Monograph"] == "❌ No"]


def predict_pathway_ui(
    drug_name: str,
    is_novel: bool,
    is_biologic: bool,
    has_data: bool
) -> tuple[str, go.Figure]:
    """Predict regulatory pathway and visualize timeline."""

    pathway = predict_regulatory_pathway(
        drug_name=drug_name,
        is_novel_molecule=is_novel,
        is_biologic=is_biologic,
        has_clinical_data=has_data
    )

    # Create markdown summary
    min_years, max_years = pathway.timeline_years
    min_cost, max_cost = pathway.cost_estimate_usd

    summary = f"""
### 📋 Predicted Pathway: **{pathway.pathway_type}**

**Timeline:** {min_years:.1f} - {max_years:.1f} years
**Cost Estimate:** ${min_cost:,} - ${max_cost:,} USD
**Success Rate:** {pathway.success_rate * 100:.1f}%

#### Eligibility Criteria:
"""
    for criterion in pathway.eligibility_criteria:
        summary += f"- {criterion}\n"

    summary += "\n#### Accelerated Program Options:\n"
    for option in pathway.accelerated_options:
        summary += f"- {option}\n"

    # Create timeline visualization
    fig = create_timeline_chart(pathway)

    return summary, fig


def create_timeline_chart(pathway) -> go.Figure:
    """Create timeline comparison chart."""

    # Calculate with accelerations
    base_timeline = calculate_timeline_with_accelerations(pathway)
    with_qidp = calculate_timeline_with_accelerations(pathway, qidp=True)
    with_all = calculate_timeline_with_accelerations(
        pathway, qidp=True, fast_track=True, breakthrough=True
    )

    scenarios = ["Base", "With QIDP", "All Programs"]
    min_times = [
        base_timeline["base_timeline"][0],
        with_qidp["accelerated_timeline"][0],
        with_all["accelerated_timeline"][0]
    ]
    max_times = [
        base_timeline["base_timeline"][1],
        with_qidp["accelerated_timeline"][1],
        with_all["accelerated_timeline"][1]
    ]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        name='Minimum Timeline',
        x=scenarios,
        y=min_times,
        marker_color='#00C4B4',
        text=[f"{t:.1f}y" for t in min_times],
        textposition='auto',
    ))

    fig.add_trace(go.Bar(
        name='Maximum Timeline',
        x=scenarios,
        y=max_times,
        marker_color='#7C8CF8',
        text=[f"{t:.1f}y" for t in max_times],
        textposition='auto',
    ))

    fig.update_layout(
        title="FDA Approval Timeline Comparison",
        xaxis_title="Scenario",
        yaxis_title="Years to Approval",
        barmode='group',
        template="plotly_white",
        height=400
    )

    return fig


def calculate_timeline_ui(
    drug_name: str,
    qidp: bool,
    fast_track: bool,
    breakthrough: bool,
    orphan: bool
) -> str:
    """Calculate timeline with selected accelerated programs."""

    # Get base pathway
    usp_info = get_usp_monograph_info(drug_name)
    pathway = predict_regulatory_pathway(
        drug_name,
        is_novel_molecule=not usp_info.has_monograph,
        is_biologic=False,
        has_clinical_data=usp_info.generic_available
    )

    # Calculate with accelerations
    result = calculate_timeline_with_accelerations(
        pathway,
        qidp=qidp,
        fast_track=fast_track,
        breakthrough=breakthrough,
        orphan=orphan
    )

    base_min, base_max = result["base_timeline"]
    acc_min, acc_max = result["accelerated_timeline"]
    programs = result["programs_applied"]
    time_saved = result["time_saved_years"]
    acceleration = result["acceleration_factor"]

    summary = f"""
### ⏱️ Timeline Calculation: **{drug_name}**

**Base Timeline:** {base_min:.1f} - {base_max:.1f} years
**Accelerated Timeline:** {acc_min:.1f} - {acc_max:.1f} years

**⚡ Time Saved:** {time_saved:.1f} years ({acceleration:.1f}% faster)

#### Programs Applied:
"""

    if programs:
        for program in programs:
            summary += f"- ✅ {program}\n"
    else:
        summary += "- None selected\n"

    summary += f"""
---

**Market Entry Estimate:** {2026 + acc_min:.0f} - {2026 + acc_max:.0f}
**Patent Clock:** Starts at IND filing (~year 2)
"""

    return summary


def generate_preind_doc_ui(drug_name: str, smiles: str, target: str) -> tuple[str, str]:
    """Generate pre-IND briefing document."""

    # Create mock candidate
    candidate = DrugCandidate(
        rank=1,
        drug_name=drug_name,
        smiles=smiles,
        target_name=target,
        binding_affinity=-8.5,
        safety_score=0.82,
        overall_score=0.85
    )

    # Generate explanations
    explanations = generate_pipeline_explanations(
        drug_name=drug_name,
        target_name=target,
        binding_affinity=-8.5,
        safety_score=0.82
    )

    # Generate report
    report = generate_regulatory_report(candidate, explanations)

    # Generate document
    document = generate_preind_briefing_document(report)

    # Also return JSON
    json_output = json.dumps(report.to_dict(), indent=2)

    return document, json_output


def show_model_explanations(drug_name: str, target_name: str) -> str:
    """Display AI model explanations for regulatory submission."""

    explanations = generate_pipeline_explanations(
        drug_name=drug_name,
        target_name=target_name,
        binding_affinity=-8.2,
        safety_score=0.79
    )

    md = """
## 🧠 AI Model Explainability Report

Per **FDA 2025 Draft Guidance** on AI in Drug Development, the following explanations
support regulatory decision-making:

---

"""

    for i, expl in enumerate(explanations, 1):
        md += f"### {i}. {expl.model_name}\n\n"
        md += f"**Prediction:** `{str(expl.prediction)[:100]}...`  \n"
        md += f"**Confidence:** {expl.confidence * 100:.1f}%\n\n"

        md += "#### Reasoning Steps:\n"
        for step in expl.reasoning_steps:
            md += f"- {step}\n"

        md += "\n#### Key Features:\n"
        for feature, importance in sorted(
            expl.feature_importance.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]:
            md += f"- **{feature}:** {importance:.2f}\n"

        md += "\n#### Citations:\n"
        for citation in expl.citations:
            md += f"- {citation}\n"

        md += "\n---\n\n"

    return md


# UI Components
def create_regulatory_tab():
    """Create the Regulatory Intelligence tab."""

    with gr.TabItem("Regulatory Intelligence"):
        gr.Markdown(_REGULATORY_INTRO)

        with gr.Tabs():
            # Tab 1: USP Monograph Filter
            with gr.TabItem("1️⃣ USP Monograph Filter"):
                gr.Markdown("### Filter Drug Library by USP Monograph Status")
                gr.Markdown(
                    "Drugs with USP monographs are eligible for the **505(b)(2) pathway**, "
                    "which can reduce development time by **40-60%**."
                )

                with gr.Row():
                    show_all = gr.Button("📚 Show All Drugs", variant="secondary")
                    show_with_monograph = gr.Button("✅ Show USP Monograph Drugs", variant="primary")
                    show_without_monograph = gr.Button("❌ Show Novel Molecules", variant="secondary")

                monograph_table = gr.Dataframe(
                    value=get_monograph_drugs(),
                    label="Drug Library",
                    interactive=False
                )

                show_all.click(lambda: get_monograph_drugs(), outputs=[monograph_table])
                show_with_monograph.click(lambda: filter_drugs_by_monograph(True), outputs=[monograph_table])
                show_without_monograph.click(lambda: filter_drugs_by_monograph(False), outputs=[monograph_table])

            # Tab 2: Pathway Predictor
            with gr.TabItem("2️⃣ Regulatory Pathway Predictor"):
                gr.Markdown("### Predict FDA Approval Pathway")

                with gr.Row():
                    with gr.Column():
                        drug_input = gr.Textbox(label="Drug Name", value="Meropenem")
                        is_novel_cb = gr.Checkbox(label="Novel molecule (no prior approval)", value=False)
                        is_bio_cb = gr.Checkbox(label="Biologic/protein therapeutic", value=False)
                        has_data_cb = gr.Checkbox(label="Has prior clinical data", value=True)
                        predict_btn = gr.Button("🔮 Predict Pathway", variant="primary")

                    with gr.Column(scale=2):
                        pathway_summary = gr.Markdown()
                        timeline_chart = gr.Plot(label="Timeline Comparison")

                predict_btn.click(
                    predict_pathway_ui,
                    [drug_input, is_novel_cb, is_bio_cb, has_data_cb],
                    [pathway_summary, timeline_chart]
                )

            # Tab 3: Timeline Calculator
            with gr.TabItem("3️⃣ Timeline Calculator"):
                gr.Markdown("### Calculate Accelerated Approval Timeline")
                gr.Markdown("Select accelerated programs to see impact on development timeline")

                with gr.Row():
                    with gr.Column():
                        calc_drug = gr.Dropdown(
                            choices=list(USP_MONOGRAPH_DB.keys()),
                            value="Meropenem",
                            label="Drug Candidate"
                        )
                        qidp_cb = gr.Checkbox(label="✅ QIDP (Qualified Infectious Disease Product)", value=True)
                        ft_cb = gr.Checkbox(label="⚡ Fast Track Designation", value=False)
                        bt_cb = gr.Checkbox(label="🚀 Breakthrough Therapy", value=False)
                        orphan_cb = gr.Checkbox(label="💎 Orphan Drug Designation", value=False)
                        calc_btn = gr.Button("⏱️ Calculate Timeline", variant="primary")

                    with gr.Column(scale=2):
                        timeline_result = gr.Markdown()

                calc_btn.click(
                    calculate_timeline_ui,
                    [calc_drug, qidp_cb, ft_cb, bt_cb, orphan_cb],
                    [timeline_result]
                )

            # Tab 4: Model Explanations
            with gr.TabItem("4️⃣ AI Model Explainability"):
                gr.Markdown("### FDA-Compliant AI Transparency")
                gr.Markdown(
                    "Generate explainability reports for all AI models used in the pipeline. "
                    "Required for FDA submissions per **2025 Draft Guidance on AI in Drug Development**."
                )

                with gr.Row():
                    expl_drug = gr.Textbox(label="Drug Name", value="Meropenem")
                    expl_target = gr.Textbox(label="Target Name", value="NDM-1")
                    expl_btn = gr.Button("🧠 Generate Explanations", variant="primary")

                explanations_md = gr.Markdown()

                expl_btn.click(
                    show_model_explanations,
                    [expl_drug, expl_target],
                    [explanations_md]
                )

            # Tab 5: Pre-IND Document Generator
            with gr.TabItem("5️⃣ Pre-IND Briefing Document"):
                gr.Markdown("### Generate Pre-IND Meeting Briefing Package")
                gr.Markdown(
                    "Auto-generate a comprehensive briefing document for your FDA Pre-IND (Type B) meeting request. "
                    "Includes pathway recommendation, USP status, QIDP eligibility, and AI model transparency."
                )

                with gr.Row():
                    with gr.Column():
                        doc_drug = gr.Textbox(label="Drug Name", value="Meropenem")
                        doc_smiles = gr.Textbox(
                            label="SMILES",
                            value="CC1C2N(C1=O)C(C(S2)(C)C)C(=O)O"
                        )
                        doc_target = gr.Textbox(label="Target Protein", value="NDM-1")
                        doc_btn = gr.Button("📄 Generate Document", variant="primary", size="lg")

                    with gr.Column(scale=2):
                        gr.Markdown("#### Preview")
                        preind_doc = gr.Markdown()

                gr.Markdown("#### Export")
                preind_json = gr.Code(label="Structured Data (JSON)", language="json")

                doc_btn.click(
                    generate_preind_doc_ui,
                    [doc_drug, doc_smiles, doc_target],
                    [preind_doc, preind_json]
                )
