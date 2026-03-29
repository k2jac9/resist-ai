"""Shared fixtures for ResistAI test suite."""
import pytest


@pytest.fixture
def sample_sequence():
    """Short amino acid sequence for testing (fragment of NDM-1)."""
    return "MELPNIMHPVAKLSTALAAALMLSGCMPGEIRPTIGQQMETG"


@pytest.fixture
def sample_smiles():
    """Aspirin SMILES -- a well-known, valid molecule."""
    return "CC(=O)OC1=CC=CC=C1C(=O)O"


@pytest.fixture
def invalid_smiles():
    """A string that is not valid SMILES."""
    return "NOT_A_MOLECULE!!!"
