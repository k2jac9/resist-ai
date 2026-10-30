"""A bounded sponsor-integration path: descriptors, evidence review, and a receipt."""
from __future__ import annotations

import html
import json
from datetime import datetime, timezone

from src.models.llm_client import NebisLLM, _RESEARCH_BOUNDARY
from src.models.nebius_transport import InferenceError
from src.research_integrity import LIMITATION, descriptor_evidence


def _llm() -> NebisLLM:
    return NebisLLM()


def _valid_review(value: object) -> bool:
    if not isinstance(value, dict) or set(value) != {"summary", "limitations", "evidence_ids"}:
        return False
    summary, limits = value["summary"], value["limitations"]
    return (isinstance(summary, str) and 1 <= len(summary.strip()) <= 4000
            and isinstance(limits, list) and 1 <= len(limits) <= 8
            and all(isinstance(s, str) and 1 <= len(s.strip()) <= 1000 for s in limits)
            and value["evidence_ids"] == ["D1"])


def review_descriptors(smiles: str, use_model: bool = False) -> tuple[str, str]:
    """Compute real descriptors; request LLM commentary only on explicit opt-in.

    Schema and citation-ID checks do not establish that generated prose is scientifically
    correct. It remains unreviewed commentary even when all format checks pass.
    """
    record = {"schema_version": 1, "status": "recorded", "model_status": "not_requested",
              "created_at": datetime.now(timezone.utc).isoformat(), "clinical_validation": False,
              "descriptor_evidence": None, "model_commentary": None, "receipt": None,
              "limitations": LIMITATION}
    try:
        if type(use_model) is not bool:
            raise ValueError()
        record["descriptor_evidence"] = descriptor_evidence(smiles)
    except (ValueError, ImportError):
        record.update(status="failed", error="invalid_structure_or_missing_rdkit")
        return "Evidence review unavailable. No descriptor or model result was produced.", json.dumps(record, indent=2)
    evidence = record["descriptor_evidence"]
    if use_model:
        try:
            result = _llm().complete_result(
                "Review the limits of evidence D1. Do not recommend treatment or infer "
                "biological activity. Return only JSON with exactly these keys: "
                '{"summary":"brief evidence review","limitations":["missing evidence"],'
                '"evidence_ids":["D1"]}. Cite only D1, which contains computed descriptors, '
                "not experimental data.\nD1=" + json.dumps(evidence, sort_keys=True),
                system=_RESEARCH_BOUNDARY, max_tokens=2048, json_mode=True)
            record["receipt"] = result.to_dict()
            review = json.loads(result.text)
            if _valid_review(review):
                record["model_status"] = "response_received"
                record["model_commentary"] = review
            else:
                record.update(model_status="rejected", error="invalid_review_schema")
        except InferenceError as exc:
            record.update(model_status="unavailable", error=str(exc))
    md = "# ResistAI Evidence Brief\n\n**Computed evidence:** RDKit molecular descriptors (D1).\n\n"
    md += "| Descriptor | Value |\n|---|---:|\n"
    md += "\n".join(f"| {k.replace('_', ' ').title()} | {v:.6g} |" for k, v in evidence["values"].items())
    md += f"\n\n**Input fingerprint:** `{evidence['input_sha256']}`\n\n"
    if record["model_status"] == "response_received":
        commentary = record["model_commentary"]
        md += "## UNREVIEWED MODEL COMMENTARY\n\n" + html.escape(commentary["summary"])
        md += "\n\n" + "\n\n".join(html.escape(s) for s in commentary["limitations"])
        md += "\n\nOnly response structure and the allowed evidence ID were checked. Prose accuracy requires human review."
    elif use_model:
        md += f"**Model review unavailable:** `{record.get('error', 'unknown')}`. Computed descriptors remain available."
    else:
        md += "**Model status:** not requested. No provider call occurred."
    md += f"\n\n> {LIMITATION}\n"
    return md, json.dumps(record, indent=2, ensure_ascii=False, allow_nan=False)
