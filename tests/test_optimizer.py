"""Regression tests for MoleculeOptimizer's handling of MolMIM output.

MolMIM returns generated SMILES under the "sample" key. The optimizer used
to read "smiles"/"smi" only, silently discarding every generated molecule.
"""
from unittest.mock import MagicMock

import pytest

# The optimizer validates SMILES with RDKit at construction time.
pytest.importorskip("rdkit")

from src.sdk.optimizer import MoleculeOptimizer


class _FakeMolMIMResult:
    def __init__(self, mols):
        self.success = True
        self.molecules = mols
        self.num_generated = len(mols)
        self.score_type = "QED"


def test_optimizer_reads_molmim_sample_key():
    nim = MagicMock()
    nim.generate_molecules.return_value = _FakeMolMIMResult([
        {"sample": "CCO", "score": 0.91},
        {"sample": "CCCO", "score": 0.85},
    ])

    opt = MoleculeOptimizer(
        target_sequence="MELPNIMHPVAK",
        seed_smiles="CC(=O)Oc1ccccc1C(=O)O",
        objectives=["qed"],            # avoid binding -> no predict_binding call
        max_iterations=1,
        molecules_per_iteration=2,
        nim_client=nim,
    )
    result = opt.run()

    smiles = {c.smiles for c in result.all_candidates}
    # Pre-fix: empty (all discarded). Post-fix: both SMILES present.
    assert result.all_candidates, "optimizer discarded all MolMIM molecules"
    assert {"CCO", "CCCO"} <= smiles
