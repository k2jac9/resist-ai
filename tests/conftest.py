"""Shared fixtures for ResistAI test suite."""
import os

import pytest

# The API fails closed when RESISTAI_API_KEY is unset. Run the default test
# suite in explicit no-auth dev mode so endpoint/validation tests exercise the
# handlers. Auth enforcement itself is covered separately in test_api_auth.py.
# Must be set before src.api.server is imported (module reads it at import time).
os.environ.setdefault("RESISTAI_ALLOW_NO_AUTH", "true")


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
