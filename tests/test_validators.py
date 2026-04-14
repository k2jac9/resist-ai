"""Tests for the API request boundary validators (SMILES, protein, DNA)."""
import pytest

from src.api.server import (
    BindingRequest,
    DNAGenerateRequest,
    StructureRequest,
    _validate_dna_sequence,
    _validate_protein_sequence,
    _validate_smiles,
)


class TestProteinValidator:
    def test_accepts_standard_amino_acids(self):
        assert _validate_protein_sequence("MKTAYIAKQRQISFVKSHFSRQ") == "MKTAYIAKQRQISFVKSHFSRQ"

    def test_uppercases_and_strips_whitespace(self):
        assert _validate_protein_sequence("  mkt ayi\n") == "MKTAYI"

    def test_accepts_extended_alphabet(self):
        # B, J, O, U, X, Z, * are tolerated for ambiguous residues
        assert _validate_protein_sequence("MKTBJOUXZ*") == "MKTBJOUXZ*"

    def test_rejects_digits(self):
        with pytest.raises(ValueError, match="invalid amino acid"):
            _validate_protein_sequence("MKT123")

    def test_rejects_punctuation(self):
        with pytest.raises(ValueError, match="invalid amino acid"):
            _validate_protein_sequence("MKT@AYI")

    def test_rejects_empty(self):
        with pytest.raises(ValueError, match="empty"):
            _validate_protein_sequence("   ")


class TestDNAValidator:
    def test_accepts_acgt(self):
        assert _validate_dna_sequence("ACGTACGT") == "ACGTACGT"

    def test_accepts_n_for_unknown(self):
        assert _validate_dna_sequence("ACGNTNNNT") == "ACGNTNNNT"

    def test_accepts_u_for_rna(self):
        assert _validate_dna_sequence("ACGU") == "ACGU"

    def test_lowercase_normalized(self):
        assert _validate_dna_sequence("acgt") == "ACGT"

    def test_rejects_non_dna_letters(self):
        with pytest.raises(ValueError, match="invalid DNA bases"):
            _validate_dna_sequence("ACGX")

    def test_rejects_empty(self):
        with pytest.raises(ValueError, match="empty"):
            _validate_dna_sequence("")


class TestSmilesValidator:
    def test_accepts_aspirin(self):
        # Aspirin
        assert _validate_smiles("CC(=O)OC1=CC=CC=C1C(=O)O") == "CC(=O)OC1=CC=CC=C1C(=O)O"

    def test_accepts_ethanol(self):
        assert _validate_smiles("CCO") == "CCO"

    def test_rejects_garbage(self):
        with pytest.raises(ValueError, match="invalid SMILES"):
            _validate_smiles("NOT_A_MOLECULE!!!")

    def test_rejects_unbalanced_brackets(self):
        with pytest.raises(ValueError, match="invalid SMILES"):
            _validate_smiles("C(C(C")


class TestPydanticIntegration:
    """Verify validators are wired into the request models."""

    def test_binding_request_rejects_invalid_smiles(self):
        with pytest.raises(ValueError):
            BindingRequest(
                protein_sequence="MKTAYIAKQRQISFVKSHFSRQA" * 2,
                ligand_smiles="NOT_A_MOLECULE!!!",
            )

    def test_binding_request_rejects_invalid_protein(self):
        with pytest.raises(ValueError):
            BindingRequest(
                protein_sequence="THIS HAS NUMBERS 12345",
                ligand_smiles="CCO",
            )

    def test_binding_request_accepts_valid_inputs(self):
        req = BindingRequest(
            protein_sequence="MKTAYIAKQRQISFVKSHFSRQA",
            ligand_smiles="CC(=O)OC1=CC=CC=C1C(=O)O",
        )
        assert req.protein_sequence == "MKTAYIAKQRQISFVKSHFSRQA"
        assert req.ligand_smiles == "CC(=O)OC1=CC=CC=C1C(=O)O"

    def test_structure_request_normalizes_sequence(self):
        req = StructureRequest(sequence="  mkt ayiakqrqisfvkshfsrq\n")
        assert req.sequence == "MKTAYIAKQRQISFVKSHFSRQ"

    def test_dna_generate_request_rejects_protein(self):
        with pytest.raises(ValueError):
            DNAGenerateRequest(sequence="MKTAYIAKQRQISFVKSHFSRQ", num_tokens=64)

    def test_dna_generate_request_accepts_dna(self):
        req = DNAGenerateRequest(sequence="ACGTACGTACGT", num_tokens=64)
        assert req.sequence == "ACGTACGTACGT"
