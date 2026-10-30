"""Research-only evidence boundaries, shared by UI callbacks and exports."""
from __future__ import annotations

import hashlib
import html
import json
import math
from datetime import datetime, timezone
from typing import Any

LIMITATION = (
    "Research software only. Computed descriptors, model structure confidence, and legacy "
    "ranking scores do not establish binding affinity, inhibition, antimicrobial efficacy, "
    "patient safety, or regulatory eligibility. No clinical validation is established."
)


def descriptor_evidence(smiles: str) -> dict[str, Any]:
    """Calculate descriptors for the supplied structure, without inferring drug identity."""
    if not isinstance(smiles, str) or not smiles.strip() or len(smiles) > 4096:
        raise ValueError("invalid_smiles")
    from rdkit import Chem, rdBase
    from rdkit.Chem import Descriptors, rdMolDescriptors
    with rdBase.BlockLogs():
        mol = Chem.MolFromSmiles(smiles.strip())
    if mol is None or mol.GetNumAtoms() == 0 or mol.GetNumAtoms() > 1024:
        raise ValueError("invalid_smiles")
    canonical = Chem.MolToSmiles(mol, canonical=True, isomericSmiles=True)
    # Canonical atom order avoids floating-point summation drift for equivalent input encodings.
    mol = Chem.MolFromSmiles(canonical)
    return {
        "method": "RDKit molecular descriptors", "version": rdBase.rdkitVersion,
        "canonical_smiles": canonical,
        "input_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
        "clinical_validation": False, "drug_identity_verified": False,
        "values": {
            "molecular_weight": float(Descriptors.MolWt(mol)),
            "logp": float(Descriptors.MolLogP(mol)),
            "polar_surface_area": float(Descriptors.TPSA(mol)),
            "hydrogen_bond_donors": int(rdMolDescriptors.CalcNumHBD(mol)),
            "hydrogen_bond_acceptors": int(rdMolDescriptors.CalcNumHBA(mol)),
            "rotatable_bonds": int(rdMolDescriptors.CalcNumRotatableBonds(mol)),
        },
        "limitations": LIMITATION,
    }


def _text(value: Any) -> str:
    return html.escape(str(value)).replace("|", "&#124;").replace("\n", " ").replace("\r", " ")


def report_document(data: dict, *, simulated: bool) -> tuple[str, str]:
    """Export the actual result object while refusing to certify legacy metadata."""
    if not isinstance(data, dict) or type(simulated) is not bool:
        raise ValueError("invalid_report_input")
    raw = json.loads(json.dumps(data, allow_nan=False))
    for key in ("targets", "top_candidates", "candidates"):
        if key in raw and (not isinstance(raw[key], list) or any(not isinstance(v, dict) for v in raw[key])):
            raise ValueError("invalid_report_collection")
    meta = raw.get("metadata")
    # Source-reported simulation cannot be upgraded by a requested display mode.
    simulated = simulated or (isinstance(meta, dict) and meta.get("demo_mode") is True)
    kind = "simulated" if simulated else "unverified_legacy_output"
    export = {
        "schema_version": 1, "status": "result_recorded", "evidence_status": kind,
        "clinical_validation": False, "provider_inference_verified": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "limitations": LIMITATION, "raw_results": raw,
    }
    candidates = raw.get("top_candidates", raw.get("candidates", []))
    targets = raw.get("targets", [])
    count = len(candidates) if isinstance(candidates, list) else 0
    target_count = len(targets) if isinstance(targets, list) else 0
    label = "SIMULATED: explicitly selected fixture data" if simulated else "UNVERIFIED LEGACY OUTPUT: execution is not scientific validation"
    md = (
        f"# ResistAI Research Record\n\n**Evidence status:** {label}\n\n"
        f"**Input label:** {_text(raw.get('pathogen', 'unspecified'))}\n\n"
        f"**Recorded target entries:** {target_count} | **Candidate entries:** {count}\n\n"
        "The JSON export contains the returned data under `raw_results`. Legacy field names "
        "such as `binding_affinity`, `safety_score`, `models_used` and regulatory pathways "
        "are retained for auditability, not endorsed as measured or verified findings.\n\n"
        "No approval timelines, treatment recommendations, or model-validation claims are inferred.\n\n"
        f"> {LIMITATION}\n"
    )
    return md, json.dumps(export, indent=2, ensure_ascii=False, allow_nan=False)


def error_document(code: str) -> tuple[str, str]:
    """Export a failure, never substitute a successful fixture run."""
    allowed = {"pipeline_failed", "pipeline_unavailable", "invalid_input", "invalid_result"}
    safe_code = code if code in allowed else "pipeline_failed"
    return (
        f"# Research run unavailable\n\n**Status:** {safe_code}\n\nNo result was produced.",
        json.dumps({"schema_version": 1, "status": "failed", "error": safe_code,
                    "clinical_validation": False, "provider_inference_verified": False,
                    "raw_results": None}, indent=2),
    )


def binding_document(result: Any) -> str:
    """Describe a received co-folding response without converting confidence to affinity."""
    if getattr(result, "success", False) is not True:
        raise ValueError("binding_unavailable")
    values = []
    observed = getattr(result, "observed_fields", None)
    for attr, label, ceiling in (
        ("confidence_score", "Structure confidence", 1),
        ("ptm_score", "pTM", 1), ("iptm_score", "ipTM", 1),
        ("ligand_iptm_score", "Ligand ipTM", 1),
        ("complex_plddt", "Complex pLDDT (provider-native scale)", 100),
        ("complex_iplddt", "Complex ipLDDT (provider-native scale)", 100),
    ):
        if observed is not None and attr not in observed:
            continue
        value = getattr(result, attr, None)
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= ceiling:
            raise ValueError("invalid_provider_metric")
        values.append(f"| {label} | {value:.4g} |")
    if not any(line.startswith("| Structure confidence") for line in values):
        raise ValueError("missing_provider_metric")
    return (
        "### Boltz-2 response received\n\n"
        "These are structural confidence metrics, not measured binding affinity or evidence "
        "of enzyme inhibition. Their scales are preserved rather than converted into clinical probabilities.\n\n"
        "| Metric | Returned value |\n|---|---:|\n" + "\n".join(values)
        + f"\n\n> {LIMITATION}\n"
    )
