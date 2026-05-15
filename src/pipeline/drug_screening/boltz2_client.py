# DEPRECATED: Use src.models.nim_client.NIMClient instead
"""Boltz-2 binding prediction client for AMR-AI drug screening.

Generates YAML inputs for Boltz-2 and calls the Nebius NIM API for
binding affinity predictions.  Falls back to a heuristic scoring
function when the API is unavailable.
"""

from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass, field
from typing import Optional

import yaml

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI

    OPENAI_SDK_AVAILABLE = True
except ImportError:
    OPENAI_SDK_AVAILABLE = False

from src.utils.chemistry import compute_descriptors, RDKIT_AVAILABLE

if RDKIT_AVAILABLE:
    from rdkit import Chem


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class BindingResult:
    """Result of a single binding prediction."""

    affinity_probability: float  # 0-1 binder score
    affinity_value: float  # log10 IC50 in uM
    confidence_score: float  # model confidence 0-1
    structure_path: Optional[str] = None  # path to predicted structure


# ---------------------------------------------------------------------------
# Known antibiotic scaffolds (SMARTS) for heuristic scoring
# ---------------------------------------------------------------------------

_ANTIBIOTIC_SCAFFOLDS: list[str] = [
    "[#7]1~[#6]~[#6]~[#7]~[#6]~[#6]~1",  # pyrimidine
    "C1=CC=C2C(=C1)C(=O)C3=CC=CC=C3C2=O",  # anthraquinone
    "O=C1CC(=O)N([*])C1",  # beta-lactam core
    "[#6]1(=O)[#7][#6][#6][#16]1",  # thiazolidine (penam core)
    "c1cc2c(cc1)oc(=O)c(c2O)C(=O)",  # coumarin / fluoroquinolone-like
    "O=C(O)c1cn(*)c2cc(F)c(*)cc12",  # fluoroquinolone
]


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class Boltz2Client:
    """Client for Boltz-2 binding affinity prediction via Nebius NIM."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.tokenfactory.nebius.com/v1",
        model: str = "boltz-2",
    ) -> None:
        self._api_key = api_key or os.getenv("NEBIUS_API_KEY", "")
        self._base_url = base_url
        self._model = model

    # -- public API ---------------------------------------------------------

    def predict_binding(
        self,
        protein_sequence: str,
        ligand_smiles: str,
        protein_id: str = "A",
        ligand_id: str = "B",
    ) -> BindingResult:
        """Predict binding affinity between a protein and a ligand.

        Tries the Nebius NIM Boltz-2 endpoint first; on any failure falls
        back to a heuristic scoring function.
        """
        yaml_input = self._build_yaml(
            protein_sequence, ligand_smiles, protein_id, ligand_id,
        )

        result = self._call_api(yaml_input, ligand_smiles)
        if result is not None:
            return result

        logger.info("Boltz-2 API unavailable; using heuristic fallback")
        return self._heuristic_score(ligand_smiles)

    def batch_predict(
        self,
        protein_sequence: str,
        ligand_smiles_list: list[str],
        protein_id: str = "A",
        ligand_id: str = "B",
    ) -> list[BindingResult]:
        """Run binding predictions for a list of ligands against one protein."""
        return [
            self.predict_binding(protein_sequence, smi, protein_id, ligand_id)
            for smi in ligand_smiles_list
        ]

    # -- YAML generation ----------------------------------------------------

    @staticmethod
    def _build_yaml(
        protein_sequence: str,
        ligand_smiles: str,
        protein_id: str,
        ligand_id: str,
    ) -> str:
        """Build the Boltz-2 input YAML document."""
        doc: dict = {
            "sequences": [
                {"protein": {"id": protein_id, "sequence": protein_sequence}},
                {"ligand": {"id": ligand_id, "smiles": ligand_smiles}},
            ],
            "properties": [
                {"affinity": {"chain_id": ligand_id}},
            ],
        }
        return yaml.dump(doc, default_flow_style=False, sort_keys=False)

    # -- API call -----------------------------------------------------------

    def _call_api(
        self, yaml_input: str, ligand_smiles: str,
    ) -> Optional[BindingResult]:
        """Attempt to call the Nebius NIM Boltz-2 endpoint."""
        if not OPENAI_SDK_AVAILABLE or not self._api_key:
            return None

        try:
            client = OpenAI(api_key=self._api_key, base_url=self._base_url)

            response = client.chat.completions.create(
                model=self._model,
                messages=[
                    {
                        "role": "user",
                        "content": yaml_input,
                    },
                ],
                temperature=0.0,
            )

            # Parse response — Boltz-2 returns affinity fields
            content = response.choices[0].message.content or ""
            return self._parse_api_response(content)

        except Exception as exc:  # noqa: BLE001
            logger.warning("Boltz-2 API call failed: %s", exc)
            return None

    @staticmethod
    def _parse_api_response(content: str) -> Optional[BindingResult]:
        """Parse a Boltz-2 API text response into a BindingResult."""
        try:
            data = yaml.safe_load(content)
            if isinstance(data, dict):
                return BindingResult(
                    affinity_probability=float(
                        data.get("affinity_probability_binary", 0.0),
                    ),
                    affinity_value=float(
                        data.get("affinity_value_log10_ic50", 0.0),
                    ),
                    confidence_score=float(
                        data.get("confidence", 0.0),
                    ),
                    structure_path=data.get("structure_path"),
                )
        except Exception:  # noqa: BLE001
            pass
        return None

    # -- Heuristic fallback -------------------------------------------------

    @staticmethod
    def _heuristic_score(ligand_smiles: str) -> BindingResult:
        """Generate a plausible mock score using molecular properties.

        Uses molecular weight, LogP, and antibiotic scaffold matching
        to produce a deterministic but reasonable score.
        """
        # Deterministic seed from SMILES
        digest = int(hashlib.sha256(ligand_smiles.encode()).hexdigest(), 16)
        base_noise = (digest % 1000) / 10000.0  # 0.0 - 0.1

        mw: float = 350.0
        log_p: float = 2.0
        scaffold_bonus: float = 0.0

        desc = compute_descriptors(ligand_smiles)
        if desc is not None:
            mw = desc["MW"]
            log_p = desc["LogP"]

        if RDKIT_AVAILABLE:
            mol = Chem.MolFromSmiles(ligand_smiles)
            if mol is not None:
                for smarts in _ANTIBIOTIC_SCAFFOLDS:
                    pattern = Chem.MolFromSmarts(smarts)
                    if pattern and mol.HasSubstructMatch(pattern):
                        scaffold_bonus = 0.15
                        break

        # Scoring heuristic: drug-like MW (200-600) and LogP (0-5) are ideal
        mw_score = max(0.0, 1.0 - abs(mw - 400) / 400)
        logp_score = max(0.0, 1.0 - abs(log_p - 2.5) / 5.0)

        probability = min(
            1.0,
            max(0.0, 0.3 * mw_score + 0.3 * logp_score + scaffold_bonus + base_noise),
        )
        # IC50 inversely related to probability: higher probability -> lower IC50
        affinity_value = round(2.0 - 3.0 * probability, 2)  # range ~ -1 to 2

        return BindingResult(
            affinity_probability=round(probability, 4),
            affinity_value=affinity_value,
            confidence_score=round(0.3 + scaffold_bonus, 2),
            structure_path=None,
        )
