"""Actual co-folding response inspection; never synthesize fallback predictions."""
from __future__ import annotations

import json
import re

from src.research_integrity import binding_document, descriptor_evidence

_HOW_IT_WORKS = """
## Inspect a Boltz-2 response

Supply a verified protein sequence and molecular structure. A successful provider response
is not experimental validation. Structural confidence is not binding affinity, inhibition,
antimicrobial activity, or clinical efficacy. No simulated fallback is used here.
"""


def _nim():
    from src.models.nim_client import NIMClient
    return NIMClient()


def predict_binding(seq: str, smiles: str) -> tuple[str, str]:
    try:
        if not isinstance(seq, str):
            raise ValueError()
        sequence = "".join(seq.split()).upper()
        if not 10 <= len(sequence) <= 2000 or not re.fullmatch(r"[ACDEFGHIKLMNPQRSTVWY]+", sequence):
            raise ValueError()
        descriptor_evidence(smiles)
    except (ValueError, ImportError):
        return "", "Invalid input: provide a protein sequence (10-2000 standard amino acids) and valid SMILES. No prediction was made."
    payload = json.dumps({"polymers": [{"molecule_type": "protein", "sequence": sequence}],
                          "ligands": [{"smiles": smiles}]}, indent=2)
    try:
        nim = _nim()
        if not nim or not nim.available:
            return payload, "Boltz-2 unavailable: NVIDIA credentials are not configured. No prediction was made."
        result = nim.predict_binding(sequence, smiles)
        return payload, binding_document(result)
    except Exception:
        return payload, "Boltz-2 result unavailable: provider failure or invalid response. No replacement scores were generated."
