"""Shared fixtures for ResistAI test suite."""
import os

import pytest

# The API server is fail-closed by default (refuses to start without
# RESISTAI_API_KEY). The test suite runs locally without a configured key, so
# opt into insecure mode before any test module imports src.api.server.
os.environ.setdefault("RESISTAI_ALLOW_INSECURE", "1")


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
