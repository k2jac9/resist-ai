"""Tests for the 3D/2D molecular visualization HTML builders."""
import base64

from src import visualization as viz

_PDB = "ATOM      1  N   MET A   1      0.000   0.000   0.000  1.00  0.00           N\n" * 5
_SDF = "molblock\n\n\n  0  0  0  0  0  0\nM  END\n"


def test_b64_roundtrips():
    assert base64.b64decode(viz._b64("hello")).decode() == "hello"


class TestRenderProteinPdb:
    def test_empty_returns_error(self):
        assert "No PDB data" in viz.render_protein_pdb("")

    def test_embeds_iframe_and_data(self):
        html = viz.render_protein_pdb(_PDB, title="NDM-1")
        assert "<iframe" in html
        assert "NDM-1" in html
        assert viz._b64(_PDB) in html  # PDB base64-embedded


class TestRenderDockingPose:
    def test_no_protein_returns_error(self):
        assert "No protein PDB" in viz.render_docking_pose("", _SDF)

    def test_no_ligand_falls_back_to_protein(self):
        html = viz.render_docking_pose(_PDB, "")
        assert "<iframe" in html
        assert "no ligand" in html.lower()

    def test_both_models_embedded(self):
        html = viz.render_docking_pose(_PDB, _SDF, title="complex")
        assert viz._b64(_PDB) in html
        assert viz._b64(_SDF) in html


class TestRenderMolecule2d:
    def test_valid_smiles_returns_svg(self):
        svg = viz.render_molecule_2d("CCO")
        assert svg is not None
        assert "svg" in svg.lower()

    def test_invalid_smiles_returns_none(self):
        assert viz.render_molecule_2d("NOT_A_MOLECULE!!!") is None

    def test_empty_returns_none(self):
        assert viz.render_molecule_2d("") is None


class TestRenderComparison:
    def test_both_empty(self):
        html = viz.render_comparison("", "")
        assert html.count("No PDB data") == 2

    def test_two_iframes(self):
        html = viz.render_comparison(_PDB, _PDB)
        assert html.count("<iframe") == 2
