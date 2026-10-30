"""Molecular descriptors, not randomized ADMET or clinical safety verdicts."""
from __future__ import annotations

from src.research_integrity import LIMITATION, descriptor_evidence

_SAFETY_INTRO = """
### Molecular descriptor check

This calculates properties of the supplied molecular structure with RDKit.
It is not a safety prediction, ADMET model, off-target assay, or clinical recommendation.
A drug name is not verified merely because a SMILES string parses.
"""


def analyze_safety(smiles: str) -> tuple:
    """Retain the old callback signature while removing fabricated clinical results."""
    try:
        evidence = descriptor_evidence(smiles)
    except (ValueError, ImportError):
        return None, None, "Descriptor analysis unavailable: invalid SMILES or missing RDKit. No safety result was produced."
    rows = "\n".join(f"| {key.replace('_', ' ').title()} | {value:.6g} |"
                     for key, value in evidence["values"].items())
    md = (
        "### Computed molecular descriptors\n\n"
        "**Method:** RDKit molecular descriptors. This is not a safety prediction.\n\n"
        "| Descriptor | Calculated value |\n|---|---:|\n" + rows
        + f"\n\n**Canonical-input SHA-256:** `{evidence['input_sha256']}`\n\n"
        + "Molecular weight is in g/mol; polar surface area is in square angstroms; "
        "LogP is a calculated partition-coefficient descriptor; remaining fields are counts.\n\n"
        + f"> {LIMITATION}\n"
    )
    # No clinical radar or off-target result is available from descriptor calculation.
    return None, None, md
