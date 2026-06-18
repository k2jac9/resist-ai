"""ADMET property prediction with heuristic fallback using RDKit descriptors."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# SMARTS patterns for common toxicophores
TOXICOPHORE_SMARTS: dict[str, str] = {
    "nitro_aromatic": "[$(c1ccccc1[N+](=O)[O-])]",
    "aniline": "[NH2]c1ccccc1",
    "michael_acceptor": "[#6]=[#6]-[#6]=[O,N,S]",
    "epoxide": "C1OC1",
    "aldehyde": "[CH]=O",
    "acyl_halide": "[#6](=O)[F,Cl,Br,I]",
    "sulfonyl_halide": "S(=O)(=O)[F,Cl,Br,I]",
    "polycyclic_aromatic": "c1ccc2c(c1)ccc1ccccc12",
    "hydrazine": "[NH]-[NH]",
    "thiocarbonyl": "[#6](=S)",
}


@dataclass
class ADMETResult:
    """Full ADMET property prediction result."""

    absorption: dict = field(default_factory=dict)
    distribution: dict = field(default_factory=dict)
    metabolism: dict = field(default_factory=dict)
    excretion: dict = field(default_factory=dict)
    toxicity: dict = field(default_factory=dict)
    overall_safety_score: float = 0.5


def _compute_rdkit_descriptors(smiles: str) -> dict:
    """Compute molecular descriptors using RDKit."""
    try:
        from rdkit import Chem
        from rdkit.Chem import Descriptors, rdMolDescriptors
    except ImportError:
        logger.warning("RDKit not available; using placeholder descriptors")
        return _placeholder_descriptors(smiles)

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Invalid SMILES: {smiles}")

    return {
        "mw": Descriptors.MolWt(mol),
        "logp": Descriptors.MolLogP(mol),
        "tpsa": Descriptors.TPSA(mol),
        "hbd": rdMolDescriptors.CalcNumHBD(mol),
        "hba": rdMolDescriptors.CalcNumHBA(mol),
        "rotatable_bonds": rdMolDescriptors.CalcNumRotatableBonds(mol),
        "aromatic_rings": rdMolDescriptors.CalcNumAromaticRings(mol),
        "heavy_atoms": mol.GetNumHeavyAtoms(),
        "toxicophore_count": _count_toxicophores(mol),
        "ring_count": rdMolDescriptors.CalcNumRings(mol),
    }


def _placeholder_descriptors(smiles: str) -> dict:
    """Rough descriptor estimates when RDKit is unavailable."""
    length = len(smiles)
    return {
        "mw": length * 8.5,
        "logp": min(length * 0.08, 5.5),
        "tpsa": length * 2.0,
        "hbd": smiles.count("N") + smiles.count("O"),
        "hba": smiles.count("N") + smiles.count("O") + smiles.count("F"),
        "rotatable_bonds": max(0, length // 8),
        "aromatic_rings": smiles.lower().count("c1"),
        "heavy_atoms": length // 2,
        "toxicophore_count": 0,
        "ring_count": smiles.count("1") // 2 + smiles.count("2") // 2,
    }


def _count_toxicophores(mol) -> int:
    """Count the number of toxicophore substructure matches."""
    from rdkit import Chem

    count = 0
    for name, smarts in TOXICOPHORE_SMARTS.items():
        pattern = Chem.MolFromSmarts(smarts)
        if pattern and mol.HasSubstructMatch(pattern):
            count += 1
    return count


def _sigmoid(x: float) -> float:
    """Numerically stable sigmoid mapping."""
    return 1.0 / (1.0 + math.exp(-max(-500, min(500, x))))


def _heuristic_absorption(desc: dict) -> dict:
    """Predict absorption properties from descriptors."""
    logp = desc["logp"]
    tpsa = desc["tpsa"]
    mw = desc["mw"]
    hbd = desc["hbd"]

    caco2 = round(-5.5 + 0.3 * logp - 0.01 * tpsa, 3)
    hua = round(max(0, min(100, 95 - 0.5 * (tpsa - 75) - 2 * max(0, hbd - 3))), 1)
    pgp = bool(mw > 400 and hbd > 2 and tpsa > 100)

    return {
        "caco2_permeability": caco2,
        "human_intestinal_absorption": hua,
        "pgp_substrate": pgp,
    }


def _heuristic_distribution(desc: dict) -> dict:
    """Predict distribution properties."""
    logp = desc["logp"]
    mw = desc["mw"]
    tpsa = desc["tpsa"]

    vdss = round(max(0.04, 0.04 + 0.15 * logp - 0.001 * tpsa), 3)
    bbb = round(max(0, min(1, _sigmoid(0.6 * logp - 0.02 * tpsa - 0.002 * mw))), 3)
    ppb = round(min(99.9, max(10, 50 + 10 * logp + 0.05 * mw)), 1)

    return {
        "vdss": vdss,
        "bbb_penetration": bbb,
        "plasma_protein_binding": ppb,
    }


def _heuristic_metabolism(desc: dict) -> dict:
    """Predict CYP inhibition liability."""
    logp = desc["logp"]
    ar = desc["aromatic_rings"]
    mw = desc["mw"]

    base_risk = 0.1 + 0.08 * logp + 0.05 * ar
    return {
        "cyp1a2_inhibitor": round(min(1, base_risk + 0.02 * ar), 3),
        "cyp2c9_inhibitor": round(min(1, base_risk + 0.01 * (mw / 100)), 3),
        "cyp2c19_inhibitor": round(min(1, base_risk), 3),
        "cyp2d6_inhibitor": round(min(1, base_risk + 0.03 * logp), 3),
        "cyp3a4_inhibitor": round(min(1, base_risk + 0.04 * ar), 3),
    }


def _heuristic_excretion(desc: dict) -> dict:
    """Predict excretion properties."""
    mw = desc["mw"]
    logp = desc["logp"]

    clearance = round(max(0.1, 1.2 - 0.001 * mw + 0.05 * logp), 3)
    oct2 = bool(logp < 1 and mw < 400)

    return {"total_clearance": clearance, "renal_oct2_substrate": oct2}


def _heuristic_toxicity(desc: dict) -> dict:
    """Predict toxicity endpoints from descriptors."""
    logp = desc["logp"]
    mw = desc["mw"]
    tc = desc["toxicophore_count"]

    herg = round(min(1, 0.05 + 0.1 * max(0, logp - 3) + 0.02 * tc), 3)
    ames = round(min(1, 0.05 + 0.15 * tc), 3)
    hepato = round(min(1, 0.1 + 0.05 * max(0, logp - 3) + 0.1 * tc), 3)
    skin = round(min(1, 0.05 + 0.08 * tc + 0.02 * max(0, logp - 2)), 3)
    ld50 = round(max(50, 2500 - 100 * tc - 50 * max(0, logp - 3) - 0.5 * mw), 1)

    return {
        "herg_inhibition": herg,
        "ames_mutagenicity": ames,
        "hepatotoxicity": hepato,
        "skin_sensitization": skin,
        "oral_rat_ld50": ld50,
    }


def _calculate_safety_score(admet: ADMETResult) -> float:
    """Compute an overall safety score (0-1, 1 = safest)."""
    tox = admet.toxicity
    penalties = 0.0
    penalties += tox.get("herg_inhibition", 0) * 0.3
    penalties += tox.get("ames_mutagenicity", 0) * 0.25
    penalties += tox.get("hepatotoxicity", 0) * 0.25
    penalties += tox.get("skin_sensitization", 0) * 0.1

    ld50 = tox.get("oral_rat_ld50", 2000)
    if ld50 < 300:
        penalties += 0.1

    abs_score = min(1, admet.absorption.get("human_intestinal_absorption", 80) / 100)
    score = max(0, min(1, 1.0 - penalties)) * 0.7 + abs_score * 0.3
    return round(max(0, min(1, score)), 3)


class ADMETPredictor:
    """ADMET property predictor with API integration and heuristic fallback."""

    def __init__(self, api_url: str | None = None, api_key: str | None = None) -> None:
        self._api_url = api_url
        self._api_key = api_key
        self._api_available = False
        if api_url and api_key:
            self._api_available = True
            logger.info("ADMET API configured: %s", api_url)
        else:
            logger.info("No ADMET API configured; using heuristic fallback")

    def predict_admet(self, smiles: str) -> ADMETResult:
        """Predict ADMET properties for a compound.

        Args:
            smiles: SMILES string of the molecule.

        Returns:
            ADMETResult with all ADMET property predictions.
        """
        if not smiles or not smiles.strip():
            raise ValueError("SMILES string cannot be empty")

        if self._api_available:
            try:
                return self._predict_via_api(smiles)
            except Exception as exc:
                logger.warning("API prediction failed: %s; using fallback", exc)

        return self._predict_heuristic(smiles)

    def _predict_via_api(self, smiles: str) -> ADMETResult:
        """Attempt prediction via external API (pkCSM or ADMETlab)."""
        import urllib.request
        import json

        payload = json.dumps({"smiles": smiles}).encode()
        req = urllib.request.Request(
            self._api_url,
            data=payload,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self._api_key}"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())

        return ADMETResult(
            absorption=data.get("absorption", {}),
            distribution=data.get("distribution", {}),
            metabolism=data.get("metabolism", {}),
            excretion=data.get("excretion", {}),
            toxicity=data.get("toxicity", {}),
            overall_safety_score=data.get("overall_safety_score", 0.5),
        )

    def _predict_heuristic(self, smiles: str) -> ADMETResult:
        """Predict ADMET using RDKit descriptors and rule-based heuristics."""
        desc = _compute_rdkit_descriptors(smiles)

        result = ADMETResult(
            absorption=_heuristic_absorption(desc),
            distribution=_heuristic_distribution(desc),
            metabolism=_heuristic_metabolism(desc),
            excretion=_heuristic_excretion(desc),
            toxicity=_heuristic_toxicity(desc),
        )
        result.overall_safety_score = _calculate_safety_score(result)
        return result
