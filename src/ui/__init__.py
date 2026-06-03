"""UI package — assembles all tabs into a single Gradio app."""
from __future__ import annotations
import os
import tempfile

try:
    import gradio as gr
except ImportError:
    raise SystemExit("gradio is required: pip install gradio>=4.8.0")

from src.ui.common import PATHOGENS, _EXAMPLE_TARGETS, _EXAMPLE_DRUGS_SAFETY
from src.ui import tab_problem, tab_pipeline, tab_models, tab_safety, tab_viewer, tab_compare, tab_report, tab_regulatory
from src.comparison import DIMENSIONS as _CMP_DIMS


def create_app() -> gr.Blocks:
    app = gr.Blocks(title="ResistAI: AI Drug Discovery")
    with app:
        gr.HTML(
            "<div class='evolved-banner'>"
            "<h1 style='margin:0;font-size:1.9em;color:#00C4B4'>ResistAI</h1>"
            "<p style='margin:4px 0;font-size:1.1em;opacity:0.9'>"
            "AI-Orchestrated Drug Discovery for Antimicrobial Resistance</p>"
            "<div style='display:flex;justify-content:center;align-items:center;gap:6px;flex-wrap:wrap;margin:8px 0'>"
            "<span style='font-size:0.7em;color:#00C4B4;font-weight:600;margin-right:2px'>NVIDIA NIM:</span>"
            "<span style='padding:2px 7px;background:rgba(0,196,180,0.12);border:1px solid rgba(0,196,180,0.4);border-radius:10px;font-size:0.7em;color:#00C4B4'>ESMFold</span>"
            "<span style='padding:2px 7px;background:rgba(0,196,180,0.12);border:1px solid rgba(0,196,180,0.4);border-radius:10px;font-size:0.7em;color:#00C4B4'>Evo2</span>"
            "<span style='padding:2px 7px;background:rgba(0,196,180,0.12);border:1px solid rgba(0,196,180,0.4);border-radius:10px;font-size:0.7em;color:#00C4B4'>Boltz-2</span>"
            "<span style='padding:2px 7px;background:rgba(0,196,180,0.12);border:1px solid rgba(0,196,180,0.4);border-radius:10px;font-size:0.7em;color:#00C4B4'>MolMIM</span>"
            "<span style='padding:2px 7px;background:rgba(0,196,180,0.12);border:1px solid rgba(0,196,180,0.4);border-radius:10px;font-size:0.7em;color:#00C4B4'>DiffDock</span>"
            "<span style='padding:2px 7px;background:rgba(0,196,180,0.12);border:1px solid rgba(0,196,180,0.4);border-radius:10px;font-size:0.7em;color:#00C4B4'>RFdiffusion</span>"
            "<span style='padding:2px 7px;background:rgba(0,196,180,0.12);border:1px solid rgba(0,196,180,0.4);border-radius:10px;font-size:0.7em;color:#00C4B4'>ProteinMPNN</span>"
            "<span style='margin-left:8px;font-size:0.7em;color:#F59E0B;font-weight:600;margin-right:2px'>HuggingFace:</span>"
            "<span style='padding:2px 7px;background:rgba(245,158,11,0.12);border:1px solid rgba(245,158,11,0.4);border-radius:10px;font-size:0.7em;color:#F59E0B'>ESM-2 650M</span>"
            "<span style='margin-left:8px;font-size:0.7em;color:#7C8CF8;font-weight:600;margin-right:2px'>Nebius AI:</span>"
            "<span style='padding:2px 7px;background:rgba(124,140,248,0.12);border:1px solid rgba(124,140,248,0.4);border-radius:10px;font-size:0.7em;color:#7C8CF8'>Qwen3-235B</span>"
            "</div>"
            "<p style='margin:0;font-size:0.8em;color:#94A3B8'>"
            "Built at Evolved 25 Hackathon · Toronto · March 2026 &nbsp;|&nbsp; "
            "9 AI Models · 3 Providers · NVIDIA NIM + HuggingFace + Nebius AI</p></div>"
        )
        _choices = list(PATHOGENS.keys())
        with gr.Tabs():
            # ---- Problem ----
            with gr.TabItem("Problem"):
                gr.Markdown(tab_problem._PROBLEM_MD)
                gr.Markdown(tab_problem._pathogen_cards())

            # ---- Pipeline ----
            with gr.TabItem("Pipeline"):
                gr.Markdown(tab_pipeline._PIPELINE_INTRO)
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### Configure")
                        dd = gr.Dropdown(choices=_choices, value=_choices[0], label="Pathogen")
                        sl = gr.Slider(5, 10, 10, step=1, label="Drugs to screen")
                        cb = gr.Checkbox(value=True, label="Demo mode (simulated data — uncheck for live AI)")
                        btn = gr.Button("🔬 Start Analysis", variant="primary", size="lg")
                    with gr.Column(scale=3):
                        status = gr.Markdown(
                            "<div style='text-align:center;padding:20px;opacity:0.6'>"
                            "<div style='font-size:2em;margin-bottom:8px'>🔬</div>"
                            "Select a pathogen and click <b>Start Analysis</b> to run the 9-stage AI pipeline.<br>"
                            "<span style='font-size:0.85em'>Results will appear here — targets, ranked drugs, novel molecules, and AI analysis.</span>"
                            "</div>"
                        )
                        gr.Markdown("### 🎯 Targets Discovered")
                        t1 = gr.Dataframe(interactive=False)
                        gr.Markdown("### 💊 Drug Candidates (ranked)")
                        t2 = gr.Dataframe(interactive=False)
                        gr.Markdown("### 📋 Summary & Technical Details")
                        summary_md = gr.Markdown()
                btn.click(tab_pipeline.run_pipeline_ui, [dd, sl, cb], [status, t1, t2, summary_md])

            # ---- Models ----
            with gr.TabItem("Models"):
                gr.Markdown(tab_models._HOW_IT_WORKS)
                _ex_choices = list(_EXAMPLE_TARGETS.keys())
                example_dd = gr.Dropdown(
                    choices=_ex_choices, value=_ex_choices[0],
                    label="Select a pre-loaded example (or type your own below)")
                def _load_example(choice):
                    ex = _EXAMPLE_TARGETS.get(choice, {})
                    return (ex.get("sequence", ""), ex.get("smiles", ""),
                            f"**Loaded:** {ex.get('drug', '')} vs {choice.split('(')[0].strip()}")
                with gr.Row():
                    with gr.Column():
                        load_status = gr.Markdown("")
                        ts = gr.Textbox(label="Protein Sequence (the 'lock')",
                                        value=_EXAMPLE_TARGETS[_ex_choices[0]]["sequence"],
                                        lines=3)
                        tl = gr.Textbox(label="Drug SMILES (the 'key')",
                                        value=_EXAMPLE_TARGETS[_ex_choices[0]]["smiles"])
                        btn3 = gr.Button("🔑 Test Binding", variant="primary")
                    with gr.Column():
                        cy = gr.Code(label="Boltz-2 Input (YAML)", language="yaml",
                                     value="# Click 'Test Binding' to generate\n# the Boltz-2 YAML input and\n# see the binding prediction results.")
                        mr = gr.Markdown(
                            "<div style='text-align:center;padding:16px;opacity:0.5'>"
                            "Binding prediction results will appear here after you click <b>Test Binding</b>."
                            "</div>"
                        )
                example_dd.change(_load_example, [example_dd], [ts, tl, load_status])
                btn3.click(tab_models.predict_binding, [ts, tl], [cy, mr])

            # ---- Safety ----
            with gr.TabItem("Safety"):
                gr.Markdown(tab_safety._SAFETY_INTRO)
                _safety_choices = list(_EXAMPLE_DRUGS_SAFETY.keys())
                safety_dd = gr.Dropdown(
                    choices=_safety_choices, value=_safety_choices[0],
                    label="Select a drug to analyze (or paste your own SMILES below)")
                def _load_safety_example(choice):
                    return _EXAMPLE_DRUGS_SAFETY.get(choice, "")
                with gr.Row():
                    with gr.Column(scale=1):
                        sm = gr.Textbox(label="Drug SMILES (molecular notation — select an example above or paste your own)",
                                        value=_EXAMPLE_DRUGS_SAFETY[_safety_choices[0]])
                        btn4 = gr.Button("🔍 Analyze Safety", variant="primary")
                    with gr.Column(scale=2):
                        pr = gr.Plot(label="Safety Profile")
                        ot = gr.Dataframe(label="Off-Target Risks", interactive=False)
                        ms = gr.Markdown(
                            "<div style='text-align:center;padding:16px;opacity:0.5'>"
                            "Select a drug and click <b>Analyze Safety</b> to see the ADMET radar chart, "
                            "off-target risk panel, and safety score."
                            "</div>"
                        )
                safety_dd.change(_load_safety_example, [safety_dd], [sm])
                btn4.click(tab_safety.analyze_safety, [sm], [pr, ot, ms])

            # ---- Structure ----
            with gr.TabItem("Structure"):
                gr.Markdown("### 3D Protein Structure Viewer")
                gr.Markdown("Fold a protein with ESMFold and view the predicted 3D structure interactively.")
                with gr.Row():
                    with gr.Column(scale=1):
                        viewer_seq = gr.Textbox(
                            label="Protein Sequence", lines=3,
                            value="MELPNIMHPVAKLSTALAAALMLSGCMPGEIRPTIGQQMETGDQRFGDLVFRQLAPNVWQ")
                        viewer_smiles = gr.Textbox(
                            label="Drug SMILES (optional — shows 2D structure below)",
                            value="OB(O)C1CCC(CC(=O)NC2CCNC2)CC1")
                        viewer_btn = gr.Button("🔬 Fold & Visualize", variant="primary")
                        gr.Markdown(
                            "<div style='font-size:0.8em;opacity:0.5;margin-top:8px'>"
                            "Rainbow coloring = N-terminus (blue) to C-terminus (red).<br>"
                            "Drag to rotate · Scroll to zoom · Right-click to pan."
                            "</div>"
                        )
                    with gr.Column(scale=3):
                        viewer_html = gr.HTML(
                            value="<div style='text-align:center;padding:80px 20px;background:rgba(0,196,180,0.03);border:1px dashed rgba(0,196,180,0.2);border-radius:8px;min-height:450px'>"
                            "<div style='font-size:3em;opacity:0.2;margin-bottom:8px'>🧬</div>"
                            "<div style='opacity:0.4'>3D protein structure will render here</div>"
                            "<div style='opacity:0.3;font-size:0.85em;margin-top:4px'>Click <b>Fold & Visualize</b> to predict the structure using ESMFold (NVIDIA NIM)</div>"
                            "</div>",
                            label="3D Structure"
                        )
                        viewer_status = gr.Markdown()
                viewer_btn.click(tab_viewer.fold_and_visualize, [viewer_seq, viewer_smiles], [viewer_html, viewer_status])

            # ---- Compare ----
            with gr.TabItem("Compare"):
                gr.Markdown("### Compare Drug Candidates")
                gr.Markdown("**1.** Select a pathogen &rarr; **2.** Click Load Candidates &rarr; **3.** Change ranking dimension to re-sort")
                with gr.Row():
                    cmp_dd = gr.Dropdown(choices=_choices, value=_choices[0], label="Pathogen")
                    cmp_dim = gr.Dropdown(choices=_CMP_DIMS, value="Overall", label="Rank by")
                    cmp_btn = gr.Button("📊 Load Candidates", variant="primary")
                cmp_chart = gr.Plot(label="Radar Comparison")
                cmp_table = gr.Dataframe(label="Comparison Table", interactive=False)
                cmp_summary = gr.Markdown(
                    "<div style='text-align:center;padding:20px;opacity:0.5'>"
                    "Click <b>Load Candidates</b> to generate the radar comparison chart and ranking table."
                    "</div>"
                )
                cmp_btn.click(tab_compare.compare_candidates_ui, [cmp_dd, cmp_dim], [cmp_chart, cmp_table, cmp_summary])
                cmp_dim.change(tab_compare.rerank_candidates_ui, [cmp_dd, cmp_dim], [cmp_chart, cmp_table, cmp_summary])

            # ---- Report ----
            with gr.TabItem("Report"):
                gr.Markdown("### Full Report with Regulatory Pathway")
                gr.Markdown("Generates a comprehensive report with executive summary, candidate rankings, "
                            "regulatory pathway (FDA 505(b)(2)), and technical model details. Export as JSON for downstream analysis.")
                with gr.Row():
                    dd5 = gr.Dropdown(choices=_choices, value=_choices[0], label="Pathogen")
                    sl5 = gr.Slider(5, 10, 10, step=1, label="Compounds")
                    cb5 = gr.Checkbox(value=True, label="Demo mode (simulated data — uncheck for live AI)")
                    btn5 = gr.Button("📄 Generate", variant="primary")
                md5 = gr.Markdown()
                ex5 = gr.Code(label="JSON Export (structured data for downstream analysis)", language="json")
                btn5.click(tab_report.generate_report, [dd5, sl5, cb5], [md5, ex5])
                btn6 = gr.Button("💾 Download JSON")
                fo = gr.File(label="Download")
                def _save(j: str) -> str | None:
                    if not j or not j.strip():
                        return None
                    fd, p = tempfile.mkstemp(suffix=".json", prefix="amrai_")
                    with os.fdopen(fd, "w") as f:
                        f.write(j)
                    return p
                btn6.click(_save, [ex5], [fo])

            # ---- Regulatory Intelligence ----
            tab_regulatory.create_regulatory_tab()

    return app
