"""Regression tests for the MoleculeOptimizer SDK.

The key regression: MolMIM returns generated molecules under the "sample"
key. The optimizer previously read "smiles"/"smi" only, silently discarding
100% of generated molecules so optimization never advanced.
"""
from unittest.mock import MagicMock

import pytest

from src.models.nim.molmim import MolMIMResult
from src.sdk.optimizer import MoleculeOptimizer, _extract_qed

# Valid, distinct SMILES used as mocked MolMIM output.
GENERATED = [
    {"sample": "CCO", "score": 0.91},
    {"sample": "CCCO", "score": 0.88},
    {"sample": "CC(=O)O", "score": 0.82},
]


def _make_optimizer(generated):
    """Build an optimizer whose NIM client returns `generated` molecules."""
    nim = MagicMock()
    nim.generate_molecules.return_value = MolMIMResult(
        molecules=generated,
        score_type="QED",
        num_generated=len(generated),
        success=bool(generated),
    )
    return MoleculeOptimizer(
        target_sequence="MELPNIMHPVAK",
        seed_smiles="CC(=O)OC1=CC=CC=C1C(=O)O",  # aspirin
        objectives=["qed", "lipinski", "toxicity"],  # no binding -> no Boltz-2
        max_iterations=1,
        molecules_per_iteration=3,
        nim_client=nim,
    )


def test_sample_key_molecules_are_kept():
    """Molecules under the 'sample' key must produce candidates."""
    opt = _make_optimizer(GENERATED)
    result = opt.run()
    smiles = {c.smiles for c in result.all_candidates}
    assert {"CCO", "CCCO", "CC(=O)O"}.issubset(smiles)


def test_no_candidates_when_generation_empty():
    """An empty MolMIM response yields no candidates (and does not crash)."""
    opt = _make_optimizer([])
    result = opt.run()
    assert result.all_candidates == []


def test_extract_qed_reads_score_key():
    assert _extract_qed({"score": 0.77}) == pytest.approx(0.77)
    assert _extract_qed({"qed": 0.5}) == pytest.approx(0.5)
    assert _extract_qed({}) == 0.0
