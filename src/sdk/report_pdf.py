"""HTML/PDF report generator for ResistAI pipeline results."""
from __future__ import annotations

import html
import logging
import os
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)
_VERSION = "1.0.0"


def _esc(text: Any) -> str:
    return html.escape(str(text)) if text else ""


def _badge(label: str, color: str = "#00C4B4") -> str:
    return (f'<span style="background:{color};color:#fff;padding:2px 8px;'
            f'border-radius:4px;font-size:0.8em;margin-right:4px;">{_esc(label)}</span>')


def _pct_bar(value: float, max_val: float = 1.0) -> str:
    pct = min(100, max(0, (value / max_val) * 100)) if max_val else 0
    color = "#00C4B4" if pct >= 60 else "#F59E0B" if pct >= 30 else "#F43F5E"
    return (f'<div style="background:#2a2a3e;border-radius:4px;height:14px;width:100px;'
            f'display:inline-block;vertical-align:middle;">'
            f'<div style="background:{color};height:100%;width:{pct:.0f}%;'
            f'border-radius:4px;"></div></div> {pct:.0f}%')


class ReportBuilder:
    """Generates polished HTML/PDF reports from pipeline results."""

    def __init__(self, title: str = "ResistAI Discovery Report"):
        self._title = title
        self._sections: list[dict[str, str]] = []

    def add_executive_summary(
        self, pathogen: str, targets: int, candidates: int,
        models_used: list[str], duration: float, llm_summary: str = "",
    ) -> ReportBuilder:
        badges = "".join(_badge(m) for m in models_used)
        body = (
            f"<p><strong>Pathogen:</strong> {_esc(pathogen)}</p>"
            f"<p><strong>Targets identified:</strong> {targets} &nbsp;|&nbsp; "
            f"<strong>Drug candidates:</strong> {candidates} &nbsp;|&nbsp; "
            f"<strong>Duration:</strong> {duration:.1f}s</p>"
            f"<p><strong>Models:</strong> {badges}</p>"
        )
        if llm_summary:
            body += f"<blockquote>{_esc(llm_summary)}</blockquote>"
        self._sections.append({"heading": "Executive Summary", "body": body})
        return self

    def add_target_table(self, targets: list[dict]) -> ReportBuilder:
        if not targets:
            return self
        rows = "".join(
            f"<tr><td>{_esc(t.get('name',''))}</td><td><code>{_esc(t.get('pdb_code',''))}</code></td>"
            f"<td>{_esc(t.get('uniprot_id',''))}</td><td>{_pct_bar(t.get('druggability_score',0))}</td>"
            f"<td>{_esc(t.get('function',''))}</td><td>{_esc(t.get('resistance_mechanism',''))}</td></tr>"
            for t in targets)
        self._sections.append({"heading": "Target Discovery", "body": (
            "<table><thead><tr><th>Target</th><th>PDB</th><th>UniProt</th>"
            f"<th>Druggability</th><th>Function</th><th>Resistance</th></tr></thead>"
            f"<tbody>{rows}</tbody></table>")})
        return self

    def add_candidate_table(self, candidates: list[dict]) -> ReportBuilder:
        if not candidates:
            return self
        rows = ""
        for c in candidates:
            rows += (
                f"<tr><td>{_esc(c.get('rank', ''))}</td>"
                f"<td><strong>{_esc(c.get('drug_name', ''))}</strong></td>"
                f"<td><code>{_esc(c.get('smiles', '')[:50])}</code></td>"
                f"<td>{_esc(c.get('target_name', ''))}</td>"
                f"<td>{c.get('binding_affinity', 0):.3f}</td>"
                f"<td>{_pct_bar(c.get('safety_score', 0))}</td>"
                f"<td><strong>{c.get('overall_score', 0):.3f}</strong></td>"
                f"<td>{_esc(c.get('regulatory_pathway', ''))}</td></tr>"
            )
        body = (
            "<table><thead><tr><th>#</th><th>Drug</th><th>SMILES</th>"
            "<th>Target</th><th>Affinity</th><th>Safety</th>"
            "<th>Score</th><th>Pathway</th>"
            f"</tr></thead><tbody>{rows}</tbody></table>"
        )
        self._sections.append({"heading": "Ranked Drug Candidates", "body": body})
        return self

    def add_novel_molecules(self, molecules: list[dict]) -> ReportBuilder:
        if not molecules:
            return self
        rows = ""
        for i, m in enumerate(molecules, 1):
            smi = str(m.get("smiles", ""))
            rows += (
                f"<tr><td>{i}</td>"
                f"<td><code>{_esc(smi[:60])}</code></td>"
                f"<td>{m.get('score', 0):.3f}</td>"
                f"<td>{_esc(m.get('score_type', m.get('type', '')))}</td>"
                f"<td><code>{_esc(str(m.get('seed_smiles', ''))[:40])}</code></td></tr>"
            )
        body = (
            "<table><thead><tr><th>#</th><th>SMILES</th><th>Score</th>"
            f"<th>Type</th><th>Seed</th></tr></thead><tbody>{rows}</tbody></table>"
        )
        self._sections.append({"heading": "AI-Generated Novel Molecules", "body": body})
        return self

    def add_binder_design(self, designs: list[dict]) -> ReportBuilder:
        if not designs:
            return self
        items = ""
        for d in designs:
            status = "Success" if d.get("success") else "Failed"
            color = "#00C4B4" if d.get("success") else "#F43F5E"
            seqs = d.get("sequences", [])
            items += (
                f'<div style="border-left:3px solid {color};padding:8px 12px;'
                f'margin-bottom:8px;background:#2a2a3e;border-radius:0 4px 4px 0;">'
                f"<strong>{status}</strong> -- {len(seqs)} designed sequence(s)"
            )
            for s in seqs[:3]:
                items += f"<br><code>{_esc(str(s)[:80])}</code>"
            items += "</div>"
        self._sections.append({"heading": "De Novo Binder Design", "body": items})
        return self

    def add_safety_profile(self, safety_data: list[dict]) -> ReportBuilder:
        if not safety_data:
            return self
        rows = ""
        for s in safety_data:
            rec = s.get("recommendation", "?")
            rec_color = "#00C4B4" if rec == "proceed" else "#F59E0B" if rec == "caution" else "#F43F5E"
            flags = ", ".join(s.get("flags", [])) or "None"
            rows += (
                f"<tr><td><strong>{_esc(s.get('drug_name', ''))}</strong></td>"
                f"<td>{_pct_bar(s.get('safety_score', 0))}</td>"
                f"<td>{_esc(s.get('toxicity_score', 'N/A'))}</td>"
                f"<td>{_esc(flags)}</td>"
                f'<td style="color:{rec_color};font-weight:bold;">{_esc(rec)}</td></tr>'
            )
        body = (
            "<table><thead><tr><th>Drug</th><th>Safety</th><th>Toxicity</th>"
            f"<th>Flags</th><th>Rec.</th></tr></thead><tbody>{rows}</tbody></table>"
        )
        self._sections.append({"heading": "Safety & ADMET Profile", "body": body})
        return self

    def add_regulatory_pathway(self) -> ReportBuilder:
        self._sections.append({"heading": "Regulatory Pathway", "body": (
            '<div style="background:#2a2a3e;padding:16px;border-radius:8px;">'
            "<p><strong>Recommended:</strong> FDA 505(b)(2)</p><ul>"
            "<li>Leverages existing safety data for known scaffolds</li>"
            "<li>Reduced clinical trial requirements vs. NDA</li>"
            "<li>Estimated timeline: 3-5 years to approval</li>"
            "<li>AI-generated evidence package included</li></ul>"
            "<p><strong>WHO GLASS:</strong> Targets from WHO Priority Pathogen List.</p></div>"
        )})
        return self

    def add_cost_analysis(self, cost_data: dict) -> ReportBuilder:
        trad = cost_data.get("traditional_cost", 2_600_000_000)
        ai = cost_data.get("ai_cost", cost_data.get("total_cost", 0))
        savings = ((trad - ai) / trad * 100) if trad else 0
        card = ('<div style="background:#2a2a3e;padding:16px;border-radius:8px;'
                'flex:1;min-width:180px;text-align:center;">')
        body = (
            f'<div style="display:flex;gap:16px;flex-wrap:wrap;">'
            f'{card}<div style="font-size:0.85em;color:#999;">Traditional R&D</div>'
            f'<div style="font-size:1.6em;color:#e04040;">${trad:,.0f}</div></div>'
            f'{card}<div style="font-size:0.85em;color:#999;">AI-Accelerated</div>'
            f'<div style="font-size:1.6em;color:#00C4B4;">${ai:,.2f}</div></div>'
            f'{card}<div style="font-size:0.85em;color:#999;">Cost Reduction</div>'
            f'<div style="font-size:1.6em;color:#00C4B4;">{savings:.1f}%</div></div></div>'
        )
        if "breakdown" in cost_data:
            rows = "".join(f"<tr><td>{_esc(k)}</td><td>${v:,.4f}</td></tr>"
                           for k, v in cost_data["breakdown"].items())
            body += (f'<table style="margin-top:16px;"><thead><tr><th>Item</th>'
                     f"<th>Cost</th></tr></thead><tbody>{rows}</tbody></table>")
        self._sections.append({"heading": "Cost Analysis", "body": body})
        return self

    def add_model_provenance(self, models: list[dict]) -> ReportBuilder:
        if not models:
            return self
        rows = ""
        for m in models:
            rows += (
                f"<tr><td>{_badge(m.get('name', ''))}</td>"
                f"<td>{_esc(m.get('version', ''))}</td>"
                f"<td>{_esc(m.get('provider', ''))}</td>"
                f"<td>{_esc(m.get('purpose', ''))}</td>"
                f"<td><code>{_esc(m.get('endpoint', 'local'))}</code></td></tr>"
            )
        body = (
            "<table><thead><tr><th>Model</th><th>Version</th><th>Provider</th>"
            f"<th>Purpose</th><th>Endpoint</th></tr></thead><tbody>{rows}</tbody></table>"
        )
        self._sections.append({"heading": "Model Provenance", "body": body})
        return self

    # -- Rendering ---------------------------------------------------------

    def render_html(self) -> str:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        sects = "".join(
            f'<section><h2>{_esc(s["heading"])}</h2>{s["body"]}</section>'
            for s in self._sections
        )
        css = (
            ":root{--bg:#0A0F1E;--sf:#0F1829;--tx:#E2E8F0;--ac:#00C4B4;--mu:#94A3B8;--ra:#1E2D4A}"
            "*{margin:0;padding:0;box-sizing:border-box}"
            "body{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);"
            "color:var(--tx);line-height:1.6;padding:24px;max-width:1100px;margin:0 auto}"
            "header{border-bottom:3px solid var(--ac);padding-bottom:16px;margin-bottom:32px}"
            "header h1{font-size:1.8em;color:var(--ac)}"
            "header .meta{font-size:.85em;color:var(--mu);margin-top:4px}"
            "section{margin-bottom:32px}"
            "h2{color:var(--ac);font-size:1.3em;margin-bottom:12px;"
            "border-left:4px solid var(--ac);padding-left:12px}"
            "table{width:100%;border-collapse:collapse;font-size:.9em}"
            "th{background:var(--sf);color:var(--ac);padding:10px 12px;"
            "text-align:left;border-bottom:2px solid var(--ac)}"
            "td{padding:8px 12px;border-bottom:1px solid #2a2a3e}"
            "tr:nth-child(even){background:var(--ra)}"
            "code{background:#2a2a3e;padding:2px 6px;border-radius:3px;font-size:.9em}"
            "blockquote{border-left:3px solid var(--ac);padding:8px 16px;margin:12px 0;"
            "background:var(--sf);border-radius:0 4px 4px 0;font-style:italic;color:#bbb}"
            "footer{margin-top:40px;padding-top:16px;border-top:1px solid #333;"
            "font-size:.8em;color:var(--mu);text-align:center}"
            "@media print{:root{--bg:#fff;--sf:#f5f5f5;--tx:#222;--mu:#666;--ra:#f9f9f9}"
            "body{padding:0}header h1{color:#222}h2{color:#333;border-left-color:#333}"
            "th{background:#eee;color:#333;border-bottom-color:#333}"
            "code{background:#eee}blockquote{background:#f5f5f5}}"
        )
        return (
            f"<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>"
            f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{_esc(self._title)}</title><style>{css}</style></head><body>"
            f"<header><h1>{_esc(self._title)}</h1>"
            f"<div class='meta'>Generated {now} | ResistAI v{_VERSION}</div></header>"
            f"{sects}<footer>ResistAI AMR Drug Discovery Platform | "
            f"BioHack Evolved 2025</footer></body></html>"
        )

    def save(self, output_path: str) -> str:
        """Save report as HTML. Attempt PDF via weasyprint if available."""
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        html_content = self.render_html()
        html_path = output_path.rsplit(".", 1)[0] + ".html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        logger.info("HTML report saved: %s", html_path)

        pdf_path = output_path.rsplit(".", 1)[0] + ".pdf"
        try:
            from weasyprint import HTML as WeasyprintHTML  # type: ignore[import-untyped]
            WeasyprintHTML(string=html_content).write_pdf(pdf_path)
            logger.info("PDF report saved: %s", pdf_path)
            return pdf_path
        except ImportError:
            logger.debug("weasyprint not available; skipping PDF generation")
        except Exception as exc:
            logger.warning("PDF generation failed: %s", exc)
        return html_path

    # -- Factory -----------------------------------------------------------

    @classmethod
    def from_pipeline_results(cls, results: Any) -> ReportBuilder:
        """Create a pre-filled report from a PipelineResults object.

        Accepts both ``src.sdk.results.PipelineResults`` and
        ``src.models.schemas.PipelineResults`` (duck-typed).
        """
        b = cls()
        _g = getattr
        name = _g(results, "target_name", "") or _g(results, "pathogen", "")
        steps = _g(results, "steps_executed", [])
        duration = 0.0
        try:
            from datetime import datetime as _dt
            t0 = _dt.fromisoformat(str(_g(results, "started_at", "")))
            t1 = _dt.fromisoformat(str(_g(results, "finished_at", "")))
            duration = (t1 - t0).total_seconds()
        except (ValueError, TypeError, AttributeError):
            pass

        step_model = {"fold": "ESMFold", "structure": "ESMFold", "screen": "Boltz-2",
                       "dock": "DiffDock", "generate": "MolMIM", "design": "RFdiffusion"}
        models = list(dict.fromkeys(step_model[s] for s in steps if s in step_model))
        if "design" in steps:
            models.append("ProteinMPNN")
        models = models or (list(steps) if steps else ["pipeline"])

        def _to_dicts(items: list) -> list[dict]:
            return [x.to_dict() if hasattr(x, "to_dict") else x for x in items]

        # Build candidates from screening hits or top_candidates
        top = _g(results, "top_candidates", [])
        hits = _g(results, "screening_hits", [])
        if top:
            cands = _to_dicts(top)
        elif hits:
            cands = [{"rank": i, "drug_name": _g(h, "drug_name", ""),
                       "smiles": _g(h, "smiles", ""), "target_name": name,
                       "binding_affinity": _g(h, "confidence", 0), "safety_score": 0.0,
                       "overall_score": _g(h, "confidence", 0),
                       "regulatory_pathway": "505(b)(2)"} for i, h in enumerate(hits, 1)]
        else:
            cands = []

        targets = _to_dicts(_g(results, "targets", []))
        novel = [m.to_dict() if hasattr(m, "to_dict") else
                 {"smiles": _g(m, "smiles", ""), "score": _g(m, "score", 0),
                  "score_type": _g(m, "score_type", ""), "seed_smiles": _g(m, "seed_smiles", "")}
                 for m in _g(results, "novel_molecules", [])]
        binder = _g(results, "binder_design", None)
        binders = [{"success": _g(binder, "success", False),
                     "sequences": _g(binder, "sequences", [])}] if binder else []
        safety = _to_dicts(_g(results, "safety_reports", []))
        analysis = _g(results, "analysis", None)

        b.add_executive_summary(name, len(targets) or 1, len(cands), models,
                                duration, analysis or "")
        if targets:
            b.add_target_table(targets)
        if cands:
            b.add_candidate_table(cands)
        if novel:
            b.add_novel_molecules(novel)
        if binders:
            b.add_binder_design(binders)
        if safety:
            b.add_safety_profile(safety)
        b.add_regulatory_pathway()
        b.add_model_provenance([{"name": m, "version": "latest",
                                  "provider": "NVIDIA BioNeMo / OSS",
                                  "purpose": "AMR target discovery",
                                  "endpoint": "NIM API"} for m in models])
        return b
