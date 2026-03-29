"""Boltz-2 protein-ligand binding prediction mixin."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Boltz2Result:
    """Protein-ligand binding prediction result."""
    confidence_score: float = 0.0
    ptm_score: float = 0.0
    iptm_score: float = 0.0
    ligand_iptm_score: float = 0.0
    complex_plddt: float = 0.0
    complex_iplddt: float = 0.0
    structure_cif: str = ""
    elapsed_ms: float = 0.0
    success: bool = False
    raw_affinities: dict = field(default_factory=dict)


class Boltz2Mixin:
    """Mixin providing predict_binding() for NIMClient."""

    def predict_binding(self, protein_sequence: str, ligand_smiles: str) -> Boltz2Result:
        """Predict protein-ligand binding using Boltz-2.

        Args:
            protein_sequence: Amino acid sequence of the target protein.
            ligand_smiles: SMILES string of the ligand/drug.

        Returns:
            Boltz2Result with confidence scores and structure.
        """
        payload = {
            "polymers": [{"molecule_type": "protein", "sequence": protein_sequence}],
            "ligands": [{"smiles": ligand_smiles}],
        }
        try:
            data = self._post("boltz2", payload, timeout=180)
            if isinstance(data, str):
                return Boltz2Result()

            cif = ""
            output_files = data.get("output_files", [])
            if output_files:
                cif = output_files[0].get("content", "")

            confidence_scores = data.get("confidence_scores", [0.0])
            ptm_scores = data.get("ptm_scores", [0.0])
            iptm_scores = data.get("iptm_scores", [0.0])
            ligand_iptm = data.get("ligand_iptm_scores", [0.0])
            plddt = data.get("complex_plddt_scores", [0.0])
            iplddt = data.get("complex_iplddt_scores", [0.0])

            return Boltz2Result(
                confidence_score=confidence_scores[0] if confidence_scores else 0.0,
                ptm_score=ptm_scores[0] if ptm_scores else 0.0,
                iptm_score=iptm_scores[0] if iptm_scores else 0.0,
                ligand_iptm_score=ligand_iptm[0] if ligand_iptm else 0.0,
                complex_plddt=plddt[0] if plddt else 0.0,
                complex_iplddt=iplddt[0] if iplddt else 0.0,
                structure_cif=cif,
                elapsed_ms=data.get("_elapsed_ms", 0),
                success=True,
                raw_affinities=data.get("affinities", {}),
            )
        except Exception as exc:
            logger.error("Boltz-2 error: %s", exc)
            return Boltz2Result()
