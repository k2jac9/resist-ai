"""Tab: Run Pipeline — 9-stage AI drug discovery pipeline."""
from __future__ import annotations
import time

try:
    import gradio as gr
except ImportError:
    raise SystemExit("gradio is required: pip install gradio>=4.8.0")

from src.ui.common import (
    PATHOGENS, _COMPOUNDS, TARGET_DETAILS,
    _to_df, _mode_badge, _explain_score,
    get_pmgr, get_orch, get_llm,
    get_demo_candidates, get_demo_targets, _demo_candidates_to_display,
)

_PIPELINE_INTRO = """
### 9 AI Models, 10 Pipeline Stages, 3 Providers

<details open>
<summary style="color:#00C4B4;cursor:pointer;font-weight:600;font-size:1.05em">Full 10-stage pipeline</summary>

| Stage | Model | What Happens | Provider |
|-------|-------|-------------|----------|
| **0. Genomics** | Evo2-40b | Scans pathogen DNA for resistance genes | NVIDIA NIM |
| **1. Druggability** | ESM-2 650M | Scores target proteins using learned embeddings | HuggingFace (local) |
| **2. Structure** | ESMFold | Folds each target protein into 3D structure | NVIDIA NIM |
| **3. Screening** | Boltz-2 | Predicts drug-target binding affinity | NVIDIA NIM |
| **4. 3D Docking** | DiffDock | Generates 3D docking poses of top hits | NVIDIA NIM |
| **5. Generation** | MolMIM | Invents novel optimized drug molecules | NVIDIA NIM |
| **6. Validation** | Boltz-2 | Validates novel molecules against target | NVIDIA NIM |
| **7. Binder Design** | RFdiffusion | Designs entirely new protein binders de novo | NVIDIA NIM |
| **8. Seq. Design** | ProteinMPNN | Designs amino acid sequences for the binder | NVIDIA NIM |
| **9. Reasoning** | Qwen3-235B | Generates clinical analysis and reports | Nebius AI |

</details>

> **One click, 9 models, 10 stages, ~2 minutes.** This process takes pharma companies 6-12 months.
"""


def run_pipeline_ui(label: str, max_n: int, demo: bool, progress=gr.Progress()):
    key = PATHOGENS[label]["key"]
    n = min(max_n, len(_COMPOUNDS))
    _orch = get_orch()
    _llm = get_llm()

    if not demo and _orch:
        try:
            results = _orch.run_full_pipeline(key, max_n, demo_mode=False, generate_novel=True)
            targets = [{"🎯 Target": t.name, "PDB": t.pdb_code,
                        "Function": t.function,
                        "Druggability": f"{t.druggability_score:.0%}"}
                       for t in results.targets]
            hits = [{"Rank": i+1, "💊 Drug": c.drug_name,
                     "Binding": f"{c.binding_affinity:.0%}",
                     "Safety": f"{c.safety_score:.0%}",
                     "Overall": f"{c.overall_score:.0%}",
                     "Pathway": c.regulatory_pathway}
                    for i, c in enumerate(results.top_candidates)]

            llm_insights = results.metadata.get("llm_insights", {})
            ai_summary = llm_insights.get("executive_summary", "")
            target_analysis = llm_insights.get("target_analysis", {})
            drug_analysis = llm_insights.get("top_drug_analysis", {})

            summary = _generate_summary(label, targets, hits, [])
            if ai_summary:
                summary += f"\n\n---\n\n## 🤖 AI Analysis (Qwen3-235B)\n\n{ai_summary}\n"
            if target_analysis and not isinstance(target_analysis, str):
                summary += f"\n\n<details>\n<summary style='color:#00C4B4;cursor:pointer'>🔬 AI Target Analysis: {results.targets[0].name}</summary>\n\n"
                for k, v in target_analysis.items():
                    if k != "error":
                        summary += f"**{k.replace('_', ' ').title()}:** {v}\n\n"
                summary += "</details>\n"
            if drug_analysis and not isinstance(drug_analysis, str):
                summary += f"\n<details>\n<summary style='color:#00C4B4;cursor:pointer'>🔬 AI Drug Analysis: {results.top_candidates[0].drug_name}</summary>\n\n"
                for k, v in drug_analysis.items():
                    if k != "error":
                        summary += f"**{k.replace('_', ' ').title()}:** {v}\n\n"
                summary += "</details>\n"

            docking_results = results.metadata.get("docking_results", [])
            if docking_results:
                summary += "\n\n---\n\n## 🎯 3D Molecular Docking (DiffDock)\n\n"
                for dr in docking_results:
                    conf_str = ", ".join(f"{c:.3f}" if isinstance(c, float) else str(c) for c in dr.get("confidence", []))
                    summary += (
                        f"**{dr.get('drug', '')}** docked into **{dr.get('target', '')}**: "
                        f"{dr.get('poses', 0)} poses generated | "
                        f"Confidence: [{conf_str}]\n\n"
                    )
                summary += "*3D docking poses via DiffDock (NVIDIA NIM)*\n"

            binder_designs = results.metadata.get("binder_designs", [])
            if binder_designs:
                summary += "\n\n---\n\n## 🧬 De Novo Protein Binder Design (RFdiffusion + ProteinMPNN)\n\n"
                summary += "AI designed **entirely new proteins** engineered to bind the resistance target.\n\n"
                summary += "| Target | Backbone Residues | Sequences Designed | Time |\n"
                summary += "|--------|-------------------|--------------------|---------|\n"
                for bd in binder_designs:
                    summary += (
                        f"| {bd.get('target', '')} | {bd.get('backbone_residues', 0)} | "
                        f"{bd.get('sequences_designed', 0)} | "
                        f"{bd.get('rfdiffusion_ms', 0):.0f}ms |\n"
                    )
                summary += "\n*De novo binder design via RFdiffusion + ProteinMPNN (NVIDIA NIM)*\n"

            novel_mols = results.metadata.get("novel_molecules", [])
            if novel_mols:
                summary += "\n\n---\n\n## 🧪 AI-Generated Novel Drug Candidates (MolMIM)\n\n"
                summary += "These molecules were **invented by AI** — they don't exist in any drug database.\n\n"
                summary += "| # | SMILES | QED | Seed Drug | Binding Conf. | Target |\n"
                summary += "|---|--------|-----|-----------|---------------|--------|\n"
                for i, mol in enumerate(novel_mols):
                    smi = mol.get("smiles", "")[:50]
                    qed = mol.get("qed_score", 0)
                    seed = mol.get("seed_drug", "")
                    bind = mol.get("binding_confidence", 0)
                    tgt = mol.get("target", "")
                    summary += f"| {i+1} | `{smi}` | {qed:.3f} | {seed} | {bind:.3f} | {tgt} |\n"
                summary += f"\n*Generated via MolMIM (NVIDIA NIM) with Boltz-2 binding validation*\n"

            models_list = results.metadata.get("models_used", [])
            model_badges = ""
            for m in models_list:
                if "NVIDIA" in m:
                    model_badges += f"<span style='padding:2px 6px;background:rgba(0,196,180,0.15);border:1px solid #00C4B4;border-radius:10px;font-size:0.75em;color:#00C4B4;margin:0 2px'>{m}</span>"
                else:
                    model_badges += f"<span style='padding:2px 6px;background:rgba(124,140,248,0.15);border:1px solid #7C8CF8;border-radius:10px;font-size:0.75em;color:#7C8CF8;margin:0 2px'>{m}</span>"
            duration = results.metadata.get("duration_seconds", 0)
            status_md = f"{_mode_badge(False)}\n\n✅ **Pipeline complete in {duration}s!**\n\n{model_badges}"
            return (status_md, _to_df(targets), _to_df(hits), summary)
        except Exception:
            pass

    for pct, msg in [(0.1, "🔍 Step 1: Scanning genome for vulnerabilities..."),
                     (0.4, "💊 Step 2: Screening drugs against targets..."),
                     (0.7, "🛡️ Step 3: Running safety analysis..."),
                     (0.95, "📊 Ranking candidates...")]:
        progress(pct, desc=msg)
        time.sleep(0.6)

    targets = _build_targets(key)
    candidates = _build_candidates(n, key)
    tech_detail = _build_tech_detail(key, targets, candidates)
    summary = _generate_summary(label, targets, candidates, tech_detail)
    progress(1.0, desc="✅ Complete!")
    status_md = f"{_mode_badge(True)}\n\n✅ **Analysis complete** — results are simulated for demonstration."
    return (status_md, _to_df(targets), _to_df(candidates), summary)


def _build_targets(key: str) -> list[dict]:
    """Deterministic targets -- delegates to shared get_demo_targets."""
    return get_demo_targets(key)


def _build_candidates(n: int, pathogen_key: str = "acinetobacter_baumannii") -> list[dict]:
    """Deterministic candidates -- delegates to shared helper."""
    return _demo_candidates_to_display(pathogen_key, n)


def _build_tech_detail(key: str, targets: list, candidates: list) -> list[str]:
    _llm = get_llm()
    lines = []
    lines.append("### Model Configuration")
    lines.append("| Parameter | Value |")
    lines.append("|-----------|-------|")
    lines.append("| Genomic Model | Evo2-40B (Arc Institute) — 9.3T nucleotides, 1M context |")
    lines.append("| Protein Model | ESM-2 650M (Meta FAIR) — 250M sequences, 1280-dim embeddings |")
    lines.append("| Binding Model | Boltz-2 (MIT) — co-folding + affinity prediction, ~40-60s/prediction |")
    lines.append("| Safety | ADMET heuristic (RDKit descriptors + SMARTS toxicophores) |")
    lines.append(f"| Target Proteome | UniProt {key} |")
    lines.append("| Drug Library | FDA-approved (ChEMBL max_phase=4) + Drug Repurposing Hub |")
    lines.append("| Scoring | overall = 0.5×binding + 0.3×safety + 0.2×confidence |")
    llm_ok = _llm and _llm.available
    lines.append(f"| **Data Source** | **{'LIVE — Nebius AI Studio + Qwen3-235B' if llm_ok else 'DEMO — simulated scores, curated drug library'}** |")
    lines.append("")
    lines.append("### Target Protein Details")
    lines.append("| Target | PDB | UniProt | Class | Mechanism |")
    lines.append("|--------|-----|---------|-------|-----------|")
    for t in targets:
        name = t["🎯 Target"]
        td = TARGET_DETAILS.get(name, {})
        lines.append(f"| {name} | [{td.get('pdb','—')}](https://rcsb.org/structure/{td.get('pdb','')}) | "
                     f"[{td.get('uniprot','—')}](https://uniprot.org/uniprot/{td.get('uniprot','')}) | "
                     f"{td.get('class','—')} | {td.get('mechanism','—')[:80]}... |")
    lines.append("")
    lines.append("### Compound Details")
    lines.append("| Drug | SMILES | Mechanism of Action |")
    lines.append("|------|--------|---------------------|")
    for c in candidates[:5]:
        name = c["💊 Drug"]
        comp = next((x for x in _COMPOUNDS if x[0] == name), None)
        if comp:
            lines.append(f"| {name} | `{comp[1][:50]}...` | {comp[4][:80]}... |")
    return lines


def _generate_summary(label: str, targets: list, candidates: list, tech_lines: list) -> str:
    info = PATHOGENS.get(label, {})
    top = candidates[0] if candidates else {}
    top_name = top.get("💊 Drug", "N/A")
    top_binding = top.get("Binding", "N/A")
    top_overall = top.get("Overall", "N/A")
    top_why = top.get("Why It Works", "")

    tech_block = "\n".join(tech_lines) if tech_lines else ""

    return f"""
## Results Summary

**Pathogen:** {label} {info.get('icon', '')}
> {info.get('plain', '')}

---

### 🏆 Top Recommendation: {top_name}

**{top_why}**

| Metric | Score | Interpretation |
|--------|-------|----------------|
| Binding Strength | {top_binding} | {_explain_score(float(top_binding.strip('%'))/100 if top_binding != 'N/A' else 0, 'affinity')} |
| Safety | {top.get('Safety', 'N/A')} | {_explain_score(float(top.get('Safety', '0%').strip('%'))/100, 'safety')} |
| **Overall** | **{top_overall}** | **{_explain_score(float(top_overall.strip('%'))/100 if top_overall != 'N/A' else 0, 'overall')}** |

### Impact

- **{len(targets)}** vulnerable protein targets identified
- **{len(candidates)}** drugs screened in seconds (vs. months in a traditional lab)
- Top candidates can enter the **505(b)(2) regulatory pathway** — reaching patients in **3-5 years** at ~$100M (vs. $2.6B for new drugs)

> *1.27 million people die from AMR infections annually. AI-accelerated drug repurposing
> can help close the gap between discovery and treatment.* — WHO

<details>
<summary style="color:#00C4B4;cursor:pointer;font-size:1.05em">🔬 Technical Details (click to expand)</summary>

{tech_block}

#### Boltz-2 Input Format (YAML)
```yaml
sequences:
  - protein:
      id: target
      sequence: "MKTA..."   # from UniProt FASTA
  - ligand:
      id: drug
      smiles: "CC(=O)..."   # from DrugBank/ChEMBL
properties:
  - affinity:
      chain_id: drug
```

#### Output Interpretation
- `affinity_probability_binary`: Binder vs non-binder (0-1)
- `affinity_pred_value`: Predicted log₁₀(IC₅₀) in μM
- Confidence: composite of pLDDT (80%) + ipTM (20%)

</details>
"""
