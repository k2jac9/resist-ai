"""Research UI: computed evidence first, with legacy workflows explicitly qualified."""
from __future__ import annotations

import gradio as gr

from src.research_execution import PATHOGEN_LABELS
from src.research_review import review_descriptors
from src.ui import tab_models, tab_pipeline, tab_report, tab_safety


def _descriptor_markdown(smiles: str) -> str:
    return tab_safety.analyze_safety(smiles)[2]


def create_app() -> gr.Blocks:
    with gr.Blocks(title="ResistAI: Research Evidence") as app:
        gr.Markdown("# ResistAI\nResearch evidence, explicit uncertainty, inspectable model responses.\n\n"
                    "**Research only.** No clinical, biological, or regulatory validation is established.")
        with gr.Tabs():
            with gr.TabItem("Evidence Review"):
                gr.Markdown("Compute molecular descriptors, then optionally ask NVIDIA Nemotron on Nebius "
                            "to review what the evidence does and does not establish. "
                            "The default `CCO` is a software test input, not a proposed AMR treatment.")
                smiles = gr.Textbox(value="CCO", label="Molecular SMILES")
                use_model = gr.Checkbox(value=False, label="Request Nebius/Nemotron commentary (uses provider credits)")
                build = gr.Button("Build evidence brief", variant="primary")
                brief = gr.Markdown()
                receipt = gr.Code(label="Evidence record and provider receipt", language="json")
                build.click(review_descriptors, [smiles, use_model], [brief, receipt],
                            concurrency_id="provider-work", concurrency_limit=1)
            with gr.TabItem("Co-folding Response"):
                gr.Markdown(tab_models._HOW_IT_WORKS)
                sequence = gr.Textbox(label="Protein sequence (verify identity externally)", lines=4)
                ligand = gr.Textbox(label="Molecular SMILES (verify identity externally)")
                run = gr.Button("Request Boltz-2 response", variant="primary")
                payload = gr.Code(label="Submitted request payload", language="json")
                result = gr.Markdown()
                run.click(tab_models.predict_binding, [sequence, ligand], [payload, result],
                          concurrency_id="provider-work", concurrency_limit=1)
            with gr.TabItem("Descriptors"):
                gr.Markdown(tab_safety._SAFETY_INTRO)
                structure = gr.Textbox(value="CCO", label="Molecular SMILES")
                check = gr.Button("Calculate descriptors")
                descriptor_result = gr.Markdown()
                check.click(_descriptor_markdown, [structure], [descriptor_result])
            with gr.TabItem("Legacy Pipeline (Unverified)"):
                gr.Markdown(tab_pipeline._PIPELINE_INTRO)
                labels = list(PATHOGEN_LABELS)
                pathogen = gr.Dropdown(choices=labels, value=labels[0], label="Legacy pathogen label")
                count = gr.Slider(1, 10, 5, step=1, label="Maximum legacy compound entries")
                simulated = gr.Checkbox(value=True, label="Use explicit simulation (no provider calls)")
                start = gr.Button("Run workflow")
                status = gr.Markdown()
                targets = gr.Dataframe(label="Target records", interactive=False)
                candidates = gr.Dataframe(label="Candidate records", interactive=False)
                summary = gr.Markdown()
                start.click(tab_pipeline.run_pipeline_ui, [pathogen, count, simulated],
                            [status, targets, candidates, summary], concurrency_id="provider-work", concurrency_limit=1)
            with gr.TabItem("Legacy Record Export"):
                gr.Markdown("This action executes a new run and exports that run's data. "
                            "Simulation is explicit. Non-simulated legacy output remains unverified. "
                            "No regulatory eligibility, cost, or approval timeline is inferred.")
                label = gr.Dropdown(choices=labels, value=labels[0], label="Legacy pathogen label")
                n = gr.Slider(1, 10, 5, step=1, label="Maximum legacy compound entries")
                demo = gr.Checkbox(value=True, label="Use explicit simulation (no provider calls)")
                export_button = gr.Button("Run and export record")
                report = gr.Markdown()
                exported = gr.Code(label="Actual returned record (JSON)", language="json")
                export_button.click(tab_report.generate_report, [label, n, demo], [report, exported],
                                    concurrency_id="provider-work", concurrency_limit=1)
        gr.Markdown("Legacy regulatory forecasts, synthetic explainability, and simulated safety verdicts "
                    "are not offered as validated capabilities in this interface.")
    return app.queue(default_concurrency_limit=1, max_size=8)
