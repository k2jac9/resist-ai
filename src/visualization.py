"""3D Molecular Visualization using 3Dmol.js via iframe srcdoc.

Gradio 6 strips <script> tags from gr.HTML. The only reliable way to run
JavaScript is via an iframe with srcdoc. PDB data is base64-encoded to
avoid escaping issues with large molecular data.
"""
from __future__ import annotations

import base64
import html as html_mod
import uuid
from typing import Optional

_3DMOL_CDN = "https://3Dmol.org/build/3Dmol-min.js"
_BG = "#0A0F1E"


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _b64(text: str) -> str:
    return base64.b64encode(text.encode()).decode()


def _iframe(inner_body: str, inner_script: str, height: int = 450) -> str:
    """Build a self-contained HTML document and embed it in an iframe."""
    doc = (
        "<!DOCTYPE html>"
        "<html><head>"
        f'<script src="{_3DMOL_CDN}"></script>'
        f"<style>*{{margin:0;padding:0;box-sizing:border-box}}"
        f"body{{background:{_BG};overflow:hidden}}</style>"
        "</head><body>"
        f"{inner_body}"
        f"<script>{inner_script}</script>"
        "</body></html>"
    )
    escaped = html_mod.escape(doc, quote=True)
    return (
        f'<iframe srcdoc="{escaped}" '
        f'style="width:100%;height:{height}px;border:1px solid #1E2D4A;'
        f'border-radius:8px;background:{_BG}" '
        f'sandbox="allow-scripts" '
        f'loading="lazy"></iframe>'
    )


def render_protein_pdb(pdb_string: str, title: str = "") -> str:
    """Render a PDB structure in 3D with cartoon representation."""
    if not pdb_string or not pdb_string.strip():
        return "<p style='color:#ff6b6b'>No PDB data provided.</p>"

    pdb_b64 = _b64(pdb_string)
    title_html = (
        f"<h4 style='color:#E2E8F0;margin:4px 0'>{title}</h4>" if title else ""
    )
    body = '<div id="v" style="width:100%;height:100%;position:absolute;top:0;left:0"></div>'
    script = (
        f'var pdb=atob("{pdb_b64}");'
        f'var v=$3Dmol.createViewer("v",{{backgroundColor:"{_BG}"}});'
        'v.addModel(pdb,"pdb");'
        'v.setStyle({},{cartoon:{color:"spectrum"}});'
        'v.addSurface($3Dmol.SurfaceType.VDW,{opacity:0.06,color:"white"});'
        'v.zoomTo();v.render();v.zoom(1.1,800);'
    )
    return f"{title_html}\n{_iframe(body, script)}"


def render_docking_pose(
    protein_pdb: str, ligand_sdf: str, title: str = ""
) -> str:
    """Render protein with a docked ligand overlay."""
    if not protein_pdb or not protein_pdb.strip():
        return "<p style='color:#ff6b6b'>No protein PDB data provided.</p>"
    if not ligand_sdf or not ligand_sdf.strip():
        return render_protein_pdb(protein_pdb, title=title or "Protein (no ligand)")

    pdb_b64 = _b64(protein_pdb)
    sdf_b64 = _b64(ligand_sdf)
    title_html = (
        f"<h4 style='color:#E2E8F0;margin:4px 0'>{title}</h4>" if title else ""
    )
    body = '<div id="v" style="width:100%;height:100%;position:absolute;top:0;left:0"></div>'
    script = (
        f'var pdb=atob("{pdb_b64}");var sdf=atob("{sdf_b64}");'
        f'var v=$3Dmol.createViewer("v",{{backgroundColor:"{_BG}"}});'
        'v.addModel(pdb,"pdb");'
        'v.setStyle({model:0},{cartoon:{color:"spectrum",opacity:0.85}});'
        'v.addModel(sdf,"sdf");'
        'v.setStyle({model:1},{stick:{colorscheme:"greenCarbon",radius:0.2}});'
        'v.addSurface($3Dmol.SurfaceType.VDW,{opacity:0.05,color:"white"},{model:0});'
        'v.zoomTo({model:1});v.zoom(0.8,600);v.render();'
    )
    return f"{title_html}\n{_iframe(body, script)}"


def render_molecule_2d(smiles: str) -> Optional[str]:
    """Generate an SVG image of a molecule from its SMILES string."""
    if not smiles or not smiles.strip():
        return None
    try:
        from rdkit import Chem
        from rdkit.Chem import Draw

        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None
        drawer = Draw.MolDraw2DSVG(400, 300)
        drawer.drawOptions().clearBackground = False
        drawer.DrawMolecule(mol)
        drawer.FinishDrawing()
        return drawer.GetDrawingText()
    except (ImportError, Exception):
        return None


def render_comparison(
    pdb1: str, pdb2: str, title1: str = "Structure A", title2: str = "Structure B"
) -> str:
    """Render two protein structures side by side for comparison."""
    parts: list[str] = ['<div style="display:flex;gap:12px;flex-wrap:wrap">']
    for pdb_data, label in [(pdb1, title1), (pdb2, title2)]:
        if not pdb_data or not pdb_data.strip():
            parts.append(
                f"<div style='flex:1;min-width:300px'>"
                f"<h4 style='color:#E2E8F0;text-align:center'>{label}</h4>"
                f"<p style='color:#ff6b6b;text-align:center'>No PDB data.</p></div>"
            )
            continue
        pdb_b64 = _b64(pdb_data)
        body = '<div id="v" style="width:100%;height:100%;position:absolute;top:0;left:0"></div>'
        script = (
            f'var pdb=atob("{pdb_b64}");'
            f'var v=$3Dmol.createViewer("v",{{backgroundColor:"{_BG}"}});'
            'v.addModel(pdb,"pdb");'
            'v.setStyle({},{cartoon:{color:"spectrum"}});'
            'v.zoomTo();v.render();'
        )
        parts.append(
            f'<div style="flex:1;min-width:300px">'
            f'<h4 style="color:#E2E8F0;text-align:center">{label}</h4>'
            f'{_iframe(body, script, height=380)}</div>'
        )
    parts.append("</div>")
    return "\n".join(parts)
