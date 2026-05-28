"""Regression test for the MoleculeOptimizer SMILES extraction.

MolMIM returns generated molecules keyed "sample"; a regression where the
optimizer only looked for "smiles"/"smi" silently discarded every molecule and
produced zero candidates.
"""
import pytest

pytest.importorskip("rdkit")

from src.models.nim.molmim import MolMIMResult
from src.sdk.optimizer import MoleculeOptimizer


class _FakeNIM:
    """Minimal stand-in returning MolMIM-shaped output keyed by 'sample'."""

    available = True

    def generate_molecules(self, **kwargs):
        return MolMIMResult(
            molecules=[
                {"sample": "CCCO", "qed": 0.80},
                {"sample": "CCCCO", "qed": 0.75},
            ],
            score_type="QED",
            num_generated=2,
            success=True,
        )


def test_optimizer_extracts_sample_smiles():
    optimizer = MoleculeOptimizer(
        target_sequence="MELPNIMH",
        seed_smiles="CCO",
        objectives=["qed"],
        max_iterations=1,
        molecules_per_iteration=2,
        nim_client=_FakeNIM(),
    )
    result = optimizer.run()
    assert result.all_candidates, "optimizer discarded all 'sample'-keyed molecules"
    smiles = {c.smiles for c in result.all_candidates}
    assert "CCCO" in smiles or "CCCCO" in smiles
