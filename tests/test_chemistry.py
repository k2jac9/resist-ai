"""Tests for src/utils/chemistry.py -- SMILES validation, descriptors, Lipinski, fingerprints, similarity."""
import numpy as np
import pytest

from src.utils.chemistry import (
    compute_descriptors,
    compute_fingerprint,
    passes_lipinski,
    tanimoto_similarity,
    validate_smiles,
)

# -- validate_smiles -----------------------------------------------------------

def test_validate_smiles_valid(sample_smiles):
    assert validate_smiles(sample_smiles) is True


def test_validate_smiles_invalid(invalid_smiles):
    assert validate_smiles(invalid_smiles) is False


def test_validate_smiles_empty():
    assert validate_smiles("") is False


# -- compute_descriptors -------------------------------------------------------

def test_compute_descriptors_keys(sample_smiles):
    desc = compute_descriptors(sample_smiles)
    assert desc is not None
    for key in ("MW", "LogP", "HBD", "HBA", "TPSA", "RotBonds"):
        assert key in desc, f"Missing descriptor key: {key}"


def test_compute_descriptors_types(sample_smiles):
    desc = compute_descriptors(sample_smiles)
    assert isinstance(desc["MW"], float)
    assert isinstance(desc["LogP"], float)


def test_compute_descriptors_invalid(invalid_smiles):
    assert compute_descriptors(invalid_smiles) is None


# -- passes_lipinski -----------------------------------------------------------

def test_passes_lipinski_aspirin(sample_smiles):
    """Aspirin (MW~180, LogP~1.2) should pass Lipinski."""
    assert passes_lipinski(sample_smiles) is True


def test_passes_lipinski_invalid(invalid_smiles):
    assert passes_lipinski(invalid_smiles) is False


# -- tanimoto_similarity -------------------------------------------------------

def test_tanimoto_self_similarity(sample_smiles):
    sim = tanimoto_similarity(sample_smiles, sample_smiles)
    assert sim is not None
    assert sim == pytest.approx(1.0)


def test_tanimoto_different_molecules():
    aspirin = "CC(=O)OC1=CC=CC=C1C(=O)O"
    caffeine = "CN1C=NC2=C1C(=O)N(C(=O)N2C)C"
    sim = tanimoto_similarity(aspirin, caffeine)
    assert sim is not None
    assert 0.0 <= sim < 1.0


def test_tanimoto_invalid_input(sample_smiles, invalid_smiles):
    assert tanimoto_similarity(sample_smiles, invalid_smiles) is None


# -- compute_fingerprint -------------------------------------------------------

def test_compute_fingerprint_shape(sample_smiles):
    fp = compute_fingerprint(sample_smiles)
    assert fp is not None
    assert isinstance(fp, np.ndarray)
    assert fp.shape == (2048,)


def test_compute_fingerprint_custom_nbits(sample_smiles):
    fp = compute_fingerprint(sample_smiles, nbits=1024)
    assert fp is not None
    assert fp.shape == (1024,)


def test_compute_fingerprint_invalid(invalid_smiles):
    assert compute_fingerprint(invalid_smiles) is None
