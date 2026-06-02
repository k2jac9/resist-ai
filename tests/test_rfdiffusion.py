"""Tests for RFdiffusion residue counting and result dataclass."""
from src.models.nim.rfdiffusion import RFdiffusionResult, _count_residues


MINI_PDB = """\
ATOM      1  N   ALA A   1       1.000   1.000   1.000  1.00  0.00           N
ATOM      2  CA  ALA A   1       1.540   1.000   1.000  1.00  0.00           C
ATOM      3  C   ALA A   1       2.000   2.400   1.000  1.00  0.00           C
ATOM      4  O   ALA A   1       1.200   3.400   1.000  1.00  0.00           O
ATOM      5  N   GLY A   2       3.320   2.500   1.000  1.00  0.00           N
ATOM      6  CA  GLY A   2       4.000   3.800   1.000  1.00  0.00           C
ATOM      7  C   GLY A   2       5.500   3.700   1.000  1.00  0.00           C
ATOM      8  O   GLY A   2       6.000   2.600   1.000  1.00  0.00           O
ATOM      9  N   VAL A   3       6.200   4.800   1.000  1.00  0.00           N
ATOM     10  CA  VAL A   3       7.700   4.900   1.000  1.00  0.00           C
END
"""


class TestCountResidues:
    def test_empty_string(self):
        assert _count_residues("") == 0

    def test_none_equivalent(self):
        assert _count_residues("") == 0

    def test_counts_ca_atoms_not_all_atoms(self):
        # 10 ATOM records but only 3 CA atoms (one per residue)
        assert _count_residues(MINI_PDB) == 3

    def test_no_ca_atoms(self):
        pdb = "ATOM      1  N   ALA A   1       1.000   1.000   1.000\n"
        assert _count_residues(pdb) == 0

    def test_hetatm_ca_counted(self):
        # HETATM with CA (e.g. non-standard amino acid)
        pdb = "HETATM    1  CA  UNK A   1       1.000   1.000   1.000\n"
        assert _count_residues(pdb) == 1

    def test_column_alignment_strict(self):
        # "CA " in a CB column position should NOT match
        pdb = "ATOM      1  CB  ALA A   1       1.000   1.000   1.000\n"
        assert _count_residues(pdb) == 0


class TestRFdiffusionResult:
    def test_defaults(self):
        r = RFdiffusionResult()
        assert r.pdb_string == ""
        assert r.num_residues == 0
        assert r.elapsed_ms == 0.0
        assert r.success is False

    def test_num_residues_reflects_ca_count(self):
        r = RFdiffusionResult(pdb_string=MINI_PDB, num_residues=3, success=True)
        assert r.num_residues == 3
