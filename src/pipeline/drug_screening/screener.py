"""Drug screening orchestrator for AMR-AI platform.

Coordinates Lipinski filtering, Boltz-2 binding prediction, and
hit ranking to produce a prioritised list of drug candidates.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Generator, Optional

from src.models.nim_client import NIMClient
from src.utils.chemistry import passes_lipinski

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ScreeningHit:
    """A single drug candidate that passed screening."""

    drug_name: str
    smiles: str
    chembl_id: str
    affinity_probability: float
    affinity_value: float
    rank: int = 0


@dataclass
class ScreeningResults:
    """Container for a full screening run."""

    target_name: str
    total_screened: int
    hits: list[ScreeningHit] = field(default_factory=list)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )


@dataclass
class ProgressUpdate:
    """Progress update yielded during screening."""

    stage: str
    current: int
    total: int
    message: str


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class DrugScreener:
    """Orchestrates the virtual drug screening pipeline."""

    def __init__(
        self,
        nim_client: Optional[NIMClient] = None,
        binding_threshold: float = 0.5,
    ) -> None:
        self._nim = nim_client or NIMClient()
        self._binding_threshold = binding_threshold

    # -- public API ---------------------------------------------------------

    def screen_drugs(
        self,
        target_sequence: str,
        target_name: str,
        drug_library: list[dict],
        max_compounds: int = 100,
    ) -> Generator[ProgressUpdate | ScreeningResults, None, None]:
        """Screen a drug library against a protein target.

        Yields ``ProgressUpdate`` instances for UI feedback and finally
        yields the ``ScreeningResults`` as the last item.

        Args:
            target_sequence: Amino-acid sequence of the protein target.
            target_name: Human-readable target name (e.g. ``"NDM-1"``).
            drug_library: List of dicts with keys ``name``, ``smiles``,
                and optionally ``chembl_id``.
            max_compounds: Cap on the number of compounds to evaluate.
        """
        # 1. Lipinski filtering
        yield ProgressUpdate("filter", 0, len(drug_library), "Applying Lipinski filter")

        lipinski_pass: list[dict] = []
        for idx, drug in enumerate(drug_library):
            smiles = drug.get("smiles", "")
            if smiles and passes_lipinski(smiles):
                lipinski_pass.append(drug)
            if len(lipinski_pass) >= max_compounds:
                break

        yield ProgressUpdate(
            "filter", len(drug_library), len(drug_library),
            f"{len(lipinski_pass)} of {len(drug_library)} passed Lipinski",
        )

        # 2. Binding prediction
        total = len(lipinski_pass)
        hits: list[ScreeningHit] = []
        for idx, drug in enumerate(lipinski_pass):
            smiles = drug.get("smiles", "")
            yield ProgressUpdate(
                "binding", idx + 1, total,
                f"Predicting binding for {drug.get('name', smiles[:20])}",
            )

            result = self._nim.predict_binding(
                protein_sequence=target_sequence,
                ligand_smiles=smiles,
            )

            # NIMClient.predict_binding returns a Boltz2Result with
            # confidence_score (0-1) and complex_plddt as affinity proxy.
            affinity_prob = result.confidence_score if result.success else 0.0
            affinity_val = result.complex_plddt if result.success else 0.0

            if affinity_prob >= self._binding_threshold:
                hits.append(
                    ScreeningHit(
                        drug_name=drug.get("name", "Unknown"),
                        smiles=smiles,
                        chembl_id=drug.get("chembl_id", ""),
                        affinity_probability=affinity_prob,
                        affinity_value=affinity_val,
                    ),
                )

        # 3. Sort and rank
        hits.sort(key=lambda h: h.affinity_probability, reverse=True)
        for rank, hit in enumerate(hits, start=1):
            hit.rank = rank

        yield ProgressUpdate(
            "complete", total, total,
            f"Screening complete: {len(hits)} hits from {total} compounds",
        )

        # 4. Final results
        yield ScreeningResults(
            target_name=target_name,
            total_screened=total,
            hits=hits,
        )

    # -- demo mode ----------------------------------------------------------

    @staticmethod
    def demo_results() -> ScreeningResults:
        """Return pre-computed demo screening results for NDM-1.

        Uses 20 known antibiotics with realistic mock affinity scores
        for demonstration and testing.
        """
        demo_hits: list[ScreeningHit] = [
            ScreeningHit("Meropenem", "C1C(C(=O)O)N2C(=O)C(C2S1(=O)=O)C(C)O", "CHEMBL127", 0.92, -1.76, 1),
            ScreeningHit("Ceftazidime", "CC(=NOC(C)(C)C(=O)O)c1csc(N)n1", "CHEMBL401", 0.88, -1.64, 2),
            ScreeningHit("Aztreonam", "CC1C(=O)N1S(=O)(=O)O", "CHEMBL158", 0.85, -1.55, 3),
            ScreeningHit("Imipenem", "C1=CN=C(N1)SCCC(=O)O", "CHEMBL560", 0.83, -1.49, 4),
            ScreeningHit("Doripenem", "CC(O)C1C2CC(=O)N2C1C(=O)O", "CHEMBL1628", 0.81, -1.43, 5),
            ScreeningHit("Cefepime", "CO/N=C(\\c1csc(N)n1)C(=O)O", "CHEMBL44", 0.78, -1.34, 6),
            ScreeningHit("Ampicillin", "CC1(C)SC2C(NC(=O)C(N)c3ccccc3)C(=O)N2C1C(=O)O", "CHEMBL174", 0.76, -1.28, 7),
            ScreeningHit("Ciprofloxacin", "O=C(O)c1cn(C2CC2)c2cc(N3CCNCC3)c(F)cc2c1=O", "CHEMBL8", 0.74, -1.22, 8),
            ScreeningHit("Levofloxacin", "CC1COc2c(N3CCN(C)CC3)c(F)cc3c(=O)c(C(=O)O)cn1c23", "CHEMBL33", 0.71, -1.13, 9),
            ScreeningHit("Amoxicillin", "CC1(C)SC2C(NC(=O)C(N)c3ccc(O)cc3)C(=O)N2C1C(=O)O", "CHEMBL1082", 0.69, -1.07, 10),
            ScreeningHit("Piperacillin", "CC1(C)SC2C(NC(=O)C(NC(=O)N3CCNC3=O)c3ccccc3)C(=O)N2C1C(=O)O", "CHEMBL484", 0.66, -0.98, 11),
            ScreeningHit("Ertapenem", "CC(O)C1C(=O)N2C(C(=O)O)=C(SC3CNC(=O)C3)CC12", "CHEMBL1160", 0.64, -0.92, 12),
            ScreeningHit("Cefotaxime", "CO/N=C(\\c1csc(N)n1)C(=O)NC1C(=O)N2C1SCC2=C", "CHEMBL161", 0.61, -0.83, 13),
            ScreeningHit("Tigecycline", "CN(C)c1cc(NC(=O)CNC(C)(C)C)c(O)c2c1CC1CC3C(N(C)C)C(O)=C(C(=O)N)C(=O)C3(O)C(O)=C1C2=O", "CHEMBL376", 0.58, -0.74, 14),
            ScreeningHit("Colistin", "CCCCCC(CC(=O)NC(CCN)C(=O)O)OC(=O)C(CC(=O)O)NC=O", "CHEMBL1489", 0.56, -0.68, 15),
            ScreeningHit("Fosfomycin", "CC1OC1P(=O)(O)O", "CHEMBL374", 0.54, -0.62, 16),
            ScreeningHit("Trimethoprim", "COc1cc(Cc2cnc(N)nc2N)cc(OC)c1OC", "CHEMBL22", 0.52, -0.56, 17),
            ScreeningHit("Sulfamethoxazole", "Cc1cc(NS(=O)(=O)c2ccc(N)cc2)no1", "CHEMBL21", 0.51, -0.53, 18),
            ScreeningHit("Vancomycin", "CC(O)C(NC(=O)C1CC(=O)NC1)C(=O)O", "CHEMBL262777", 0.50, -0.50, 19),
            ScreeningHit("Rifampicin", "CC1C=CC=C(C)C(=O)NC(=CC=CC(C)C(O)C(C)C(=O)C(C)C(OC(=O)C)C1O)C", "CHEMBL374478", 0.48, -0.44, 20),
        ]

        return ScreeningResults(
            target_name="NDM-1 (Metallo-beta-lactamase)",
            total_screened=20,
            hits=[h for h in demo_hits if h.affinity_probability >= 0.5],
        )
