"""Tab: 3D Viewer — protein folding and molecular visualization."""
from __future__ import annotations

import gradio as gr

_LOADING_HTML = (
    "<div style='text-align:center;padding:40px;color:#00C4B4;"
    "border:1px solid rgba(0,196,180,0.3);border-radius:8px;"
    "background:rgba(0,196,180,0.05)'>"
    "<div style='font-size:2em;margin-bottom:8px;animation:pulse 1.5s infinite'>"
    "&#9883;</div>"
    "<div style='font-weight:600'>Folding protein&hellip;</div>"
    "<div style='opacity:0.6;font-size:0.85em;margin-top:4px'>"
    "Calling ESMFold via NVIDIA NIM — this may take a few seconds.</div>"
    "<style>@keyframes pulse{0%,100%{opacity:0.3}50%{opacity:1}}</style>"
    "</div>"
)


def fold_and_visualize(sequence: str, smiles: str) -> tuple[str, str]:
    """Fold a protein sequence and return 3D HTML + status markdown."""
    from src.visualization import render_protein_pdb, render_molecule_2d

    if not sequence or not sequence.strip():
        return "<p style='color:#ff6b6b'>Please enter a protein sequence.</p>", ""

    seq = sequence.strip().upper()
    status_parts: list[str] = []
    pdb_string = ""

    # Show loading state via Gradio progress (visible in UI)
    progress = gr.Progress()
    progress(0.1, desc="Folding protein with ESMFold...")

    try:
        from src.models.nim_client import NIMClient
        nim = NIMClient()
        if nim.available:
            progress(0.3, desc="Sending sequence to NVIDIA NIM...")
            result = nim.fold_protein(seq)
            if result.success:
                pdb_string = result.pdb_string
                status_parts.append(
                    f"**ESMFold** completed in {result.elapsed_ms:.0f} ms "
                    f"({result.sequence_length} residues)"
                )
    except Exception:
        pass

    progress(0.7, desc="Rendering 3D structure...")

    if not pdb_string:
        status_parts.append(
            "ESMFold API unavailable -- showing placeholder. "
            "Set `NVIDIA_API_KEY` to enable real folding."
        )
        html = (
            "<div style='padding:40px;text-align:center;color:#aaa;"
            "border:1px dashed #444;border-radius:8px'>"
            "<p style='font-size:1.2em'>3D viewer requires a folded PDB structure.</p>"
            "<p>Connect ESMFold via NVIDIA NIM to fold this sequence live.</p></div>"
        )
    else:
        html = render_protein_pdb(pdb_string, title=f"Folded structure ({len(seq)} aa)")

    if smiles and smiles.strip():
        svg = render_molecule_2d(smiles.strip())
        if svg:
            html += f"<h4 style='color:#e0e0e0;margin-top:12px'>Drug (2D)</h4>{svg}"
            status_parts.append(f"Drug SMILES rendered: `{smiles.strip()[:60]}`")
        else:
            status_parts.append(
                "Could not render drug (RDKit unavailable or invalid SMILES)."
            )

    progress(1.0, desc="Done")
    return html, "\n\n".join(status_parts)
