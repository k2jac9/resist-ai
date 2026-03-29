"""Chemistry utilities built on RDKit.

Provides SMILES validation, molecular descriptor computation, Lipinski
Rule-of-Five filtering, fingerprint generation, and similarity scoring.
All functions handle invalid input gracefully by returning ``None``.
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np
from numpy.typing import NDArray

logger = logging.getLogger(__name__)

try:
    from rdkit import Chem, DataStructs
    from rdkit.Chem import Descriptors, rdMolDescriptors

    RDKIT_AVAILABLE = True
except ImportError:
    RDKIT_AVAILABLE = False
    logger.warning("RDKit not installed; chemistry utils will return None")


def validate_smiles(smiles: str) -> bool:
    """Return ``True`` if *smiles* parses into a valid molecule."""
    if not smiles or not RDKIT_AVAILABLE:
        return False
    return Chem.MolFromSmiles(smiles) is not None


def smiles_to_mol(smiles: str) -> Optional[object]:
    """Convert a SMILES string to an RDKit ``Mol`` object.

    Returns ``None`` for invalid or empty input, or if RDKit is unavailable.
    """
    if not smiles or not RDKIT_AVAILABLE:
        return None
    return Chem.MolFromSmiles(smiles)


def compute_descriptors(smiles: str) -> Optional[dict[str, float]]:
    """Compute key molecular descriptors.

    Returns a dict with MW, LogP, HBD, HBA, TPSA, and RotBonds,
    or ``None`` if the SMILES is invalid.
    """
    mol = smiles_to_mol(smiles)
    if mol is None:
        return None
    return {
        "MW": Descriptors.MolWt(mol),
        "LogP": Descriptors.MolLogP(mol),
        "HBD": float(rdMolDescriptors.CalcNumHBD(mol)),
        "HBA": float(rdMolDescriptors.CalcNumHBA(mol)),
        "TPSA": Descriptors.TPSA(mol),
        "RotBonds": float(rdMolDescriptors.CalcNumRotatableBonds(mol)),
    }


def passes_lipinski(smiles: str) -> bool:
    """Check Lipinski's Rule of Five.

    A molecule passes if it violates at most one rule:
      - MW <= 500
      - LogP <= 5
      - HBD <= 5
      - HBA <= 10

    Returns ``False`` for invalid SMILES or if RDKit is unavailable.
    """
    desc = compute_descriptors(smiles)
    if desc is None:
        return False
    violations = sum([
        desc["MW"] > 500,
        desc["LogP"] > 5,
        desc["HBD"] > 5,
        desc["HBA"] > 10,
    ])
    return violations <= 1


def compute_fingerprint(
    smiles: str, radius: int = 2, nbits: int = 2048
) -> Optional[NDArray[np.float64]]:
    """Generate a Morgan fingerprint as a numpy bit-vector.

    Args:
        smiles: Input molecule.
        radius: Morgan radius (default 2 = ECFP4).
        nbits: Bit-vector length.

    Returns:
        1-D numpy array of shape ``(nbits,)``, or ``None``.
    """
    mol = smiles_to_mol(smiles)
    if mol is None:
        return None
    fp = rdMolDescriptors.GetMorganFingerprintAsBitVect(mol, radius, nBits=nbits)
    arr = np.zeros(nbits, dtype=np.float64)
    DataStructs.ConvertToNumpyArray(fp, arr)
    return arr


def tanimoto_similarity(smiles1: str, smiles2: str) -> Optional[float]:
    """Compute Tanimoto similarity between two molecules.

    Uses Morgan fingerprints (radius=2, 2048 bits).
    Returns ``None`` if either SMILES is invalid.
    """
    mol1 = smiles_to_mol(smiles1)
    mol2 = smiles_to_mol(smiles2)
    if mol1 is None or mol2 is None:
        return None
    fp1 = rdMolDescriptors.GetMorganFingerprintAsBitVect(mol1, 2, nBits=2048)
    fp2 = rdMolDescriptors.GetMorganFingerprintAsBitVect(mol2, 2, nBits=2048)
    return float(DataStructs.TanimotoSimilarity(fp1, fp2))
