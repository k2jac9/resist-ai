"""Off-target binding analysis for drug safety assessment."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Curated list of critical human anti-targets with representative SMILES of
# known binders and associated adverse effects.
ANTI_TARGETS: list[dict] = [
    {"protein": "hERG potassium channel", "tissue": "Heart",
     "adverse": "QT prolongation, cardiac arrhythmia",
     "binder_smiles": "c1ccc2c(c1)cc1ccc(cc1n2)OCCN1CCOCC1"},
    {"protein": "5-HT2B receptor", "tissue": "Heart valves",
     "adverse": "Cardiac valvulopathy",
     "binder_smiles": "CN1CCc2c(c3ccccc3[nH]2)C1"},
    {"protein": "CYP3A4", "tissue": "Liver",
     "adverse": "Drug-drug interactions, hepatotoxicity",
     "binder_smiles": "c1ccc(-c2cc(-c3cccnc3)ncn2)cc1"},
    {"protein": "CYP2D6", "tissue": "Liver",
     "adverse": "Drug-drug interactions, altered metabolism",
     "binder_smiles": "CN(C)CCOC(c1ccccc1)c1ccccc1"},
    {"protein": "CYP1A2", "tissue": "Liver",
     "adverse": "Drug-drug interactions",
     "binder_smiles": "Cn1c(=O)c2c(ncn2C)n(C)c1=O"},
    {"protein": "Muscarinic M1 receptor", "tissue": "CNS, Heart, GI",
     "adverse": "Dry mouth, urinary retention, confusion",
     "binder_smiles": "OC(c1ccccc1)(c1ccccc1)C1CCN(CC2CCCCC2)CC1"},
    {"protein": "Muscarinic M2 receptor", "tissue": "Heart",
     "adverse": "Tachycardia, cardiac effects",
     "binder_smiles": "O=C(OC1CC2CCC(C1)N2C)C(O)(c1ccccc1)c1ccccc1"},
    {"protein": "Dopamine D2 receptor", "tissue": "CNS",
     "adverse": "Extrapyramidal symptoms, hyperprolactinemia",
     "binder_smiles": "O=c1[nH]c2ccccc2n1CCCN1CCC(O)(c2ccc(Cl)cc2)CC1"},
    {"protein": "Alpha-1 adrenergic receptor", "tissue": "Vasculature",
     "adverse": "Orthostatic hypotension, dizziness",
     "binder_smiles": "COc1ccc(CC2CNCCN2)cc1OC"},
    {"protein": "H1 histamine receptor", "tissue": "CNS",
     "adverse": "Sedation, weight gain",
     "binder_smiles": "C(=C1CCNCC1)c1ccncc1"},
    {"protein": "COX-1", "tissue": "GI, Platelets",
     "adverse": "GI bleeding, platelet dysfunction",
     "binder_smiles": "CC(=O)Oc1ccccc1C(=O)O"},
    {"protein": "GABA-A receptor", "tissue": "CNS",
     "adverse": "Sedation, respiratory depression",
     "binder_smiles": "O=C1NC(=O)c2ccccc2N1"},
    {"protein": "Sodium channel Nav1.5", "tissue": "Heart",
     "adverse": "Cardiac conduction block",
     "binder_smiles": "CCN(CC)CCOC(=O)c1ccc(N)cc1"},
    {"protein": "PDE3", "tissue": "Heart, Platelets",
     "adverse": "Arrhythmia, bleeding risk",
     "binder_smiles": "O=c1[nH]c(=O)c2nc(-c3cccc(O)c3)[nH]c2[nH]1"},
    {"protein": "PPARgamma", "tissue": "Adipose, Liver",
     "adverse": "Weight gain, edema, fracture risk",
     "binder_smiles": "O=C(CCc1ccc(O)cc1)c1ccc(OCCN2CCCCC2)cc1"},
    {"protein": "GluN (NMDA receptor)", "tissue": "CNS",
     "adverse": "Neurotoxicity, psychotomimetic effects",
     "binder_smiles": "c1ccc(C2(N)CCCCC2)cc1"},
    {"protein": "Sigma-1 receptor", "tissue": "CNS",
     "adverse": "Hallucinations, dysphoria",
     "binder_smiles": "O=C(CCCN1CCC(O)(c2ccc(Cl)cc2)CC1)c1ccc(F)cc1"},
    {"protein": "Pregnane X receptor (PXR)", "tissue": "Liver",
     "adverse": "CYP induction, drug interactions",
     "binder_smiles": "Clc1ccc(C(c2ccccc2)c2ccccc2)cc1"},
    {"protein": "Opioid mu receptor", "tissue": "CNS, GI",
     "adverse": "Respiratory depression, dependence",
     "binder_smiles": "CN1CCC23C(=O)C=CC2(O)Oc2c(O)ccc(c21)C3"},
    {"protein": "Phospholipidosis inducer (LAMP2)", "tissue": "Liver, Lung",
     "adverse": "Phospholipidosis, organ toxicity",
     "binder_smiles": "CCN(CC)CCCC(C)Nc1ccnc2cc(Cl)ccc12"},
]


@dataclass
class OffTarget:
    """A single off-target binding prediction."""

    protein_name: str
    similarity_score: float
    tissue_expression: str
    known_adverse_effects: str


@dataclass
class OffTargetReport:
    """Complete off-target analysis report."""

    drug_name: str
    num_potential_off_targets: int = 0
    off_targets: list[OffTarget] = field(default_factory=list)
    risk_level: str = "low"


def _compute_tanimoto(smiles_a: str, smiles_b: str) -> float:
    """Compute Tanimoto similarity between two molecules."""
    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem, DataStructs

        mol_a = Chem.MolFromSmiles(smiles_a)
        mol_b = Chem.MolFromSmiles(smiles_b)
        if mol_a is None or mol_b is None:
            return 0.0
        fp_a = AllChem.GetMorganFingerprintAsBitVect(mol_a, 2, nBits=2048)
        fp_b = AllChem.GetMorganFingerprintAsBitVect(mol_b, 2, nBits=2048)
        return round(DataStructs.TanimotoSimilarity(fp_a, fp_b), 4)
    except ImportError:
        return _fallback_similarity(smiles_a, smiles_b)


def _fallback_similarity(a: str, b: str) -> float:
    """Simple character-set Jaccard when RDKit is unavailable."""
    set_a = set(a)
    set_b = set(b)
    if not set_a or not set_b:
        return 0.0
    return round(len(set_a & set_b) / len(set_a | set_b), 4)


def _classify_risk(hits: list[OffTarget]) -> str:
    """Classify overall risk from off-target hits."""
    if not hits:
        return "low"
    max_sim = max(h.similarity_score for h in hits)
    cardiac_hit = any("heart" in h.tissue_expression.lower() or "cardiac" in h.known_adverse_effects.lower() for h in hits)
    if max_sim > 0.6 or (cardiac_hit and max_sim > 0.4):
        return "high"
    if max_sim > 0.35 or len(hits) >= 5:
        return "medium"
    return "low"


class OffTargetAnalyzer:
    """Analyzes potential off-target binding liabilities of a drug candidate."""

    def __init__(self, similarity_threshold: float = 0.25) -> None:
        self._threshold = similarity_threshold

    def analyze_off_targets(
        self, drug_smiles: str, target_sequence: str = ""
    ) -> OffTargetReport:
        """Scan drug against curated anti-target panel.

        Args:
            drug_smiles: SMILES of the drug candidate.
            target_sequence: Primary target protein sequence (informational).

        Returns:
            OffTargetReport with flagged off-target liabilities.
        """
        if not drug_smiles or not drug_smiles.strip():
            raise ValueError("Drug SMILES cannot be empty")

        hits: list[OffTarget] = []
        for entry in ANTI_TARGETS:
            sim = _compute_tanimoto(drug_smiles, entry["binder_smiles"])
            if sim >= self._threshold:
                hits.append(OffTarget(
                    protein_name=entry["protein"],
                    similarity_score=sim,
                    tissue_expression=entry["tissue"],
                    known_adverse_effects=entry["adverse"],
                ))

        hits.sort(key=lambda h: h.similarity_score, reverse=True)
        risk = _classify_risk(hits)

        return OffTargetReport(
            drug_name=drug_smiles[:40],
            num_potential_off_targets=len(hits),
            off_targets=hits,
            risk_level=risk,
        )
