"""Drug library manager with ChEMBL and Broad Repurposing Hub integration.

Fetches approved-drug data from public APIs, caches results in memory,
and provides a fallback set of 20 well-known FDA-approved antibiotics.
"""

from __future__ import annotations

import csv
import io
import logging
from typing import Optional

import httpx

from src.utils.config import get_settings

logger = logging.getLogger(__name__)

# -- Fallback: 20 FDA-approved antibiotics ------------------------------------

_FALLBACK_ANTIBIOTICS: list[dict[str, str]] = [
    {"name": "Amoxicillin",    "smiles": "CC1(C(N2C(S1)C(C2=O)NC(=O)C(C3=CC=C(C=C3)O)N)C(=O)O)C", "chembl_id": "CHEMBL1082", "phase": "4"},
    {"name": "Ciprofloxacin",  "smiles": "C1CC1N2C=C(C(=O)C3=CC(=C(C=C32)N4CCNCC4)F)C(=O)O", "chembl_id": "CHEMBL8", "phase": "4"},
    {"name": "Azithromycin",   "smiles": "CCC1C(C(C(N(CC(CC(C(C(C(C(=O)O1)C)OC2CC(C(C(O2)C)O)(C)OC)C)OC3C(C(CC(O3)C)N(C)C)O)(C)O)C)C)C)O)(C)O", "chembl_id": "CHEMBL529", "phase": "4"},
    {"name": "Doxycycline",    "smiles": "CC1C2C(C3C(C(=O)C(=C(C3(C(=O)C2=C(C4=C1C=CC=C4O)O)O)O)C(=O)N)N(C)C)O", "chembl_id": "CHEMBL1560", "phase": "4"},
    {"name": "Meropenem",      "smiles": "CC(C1C2CC(=C(N2C1=O)C(=O)O)SC3CC(NC3)C(=O)N(C)C)O", "chembl_id": "CHEMBL127", "phase": "4"},
    {"name": "Vancomycin",     "smiles": "CC1C(C(CC(O1)OC2C(C(C(OC2OC3=CC=C4C(=C3)OC5=C(C=C(C=C5)C(C(=O)NC(C(=O)NC4C(=O)NC6C=CC(=C(C6)OC7=CC=C(C=C7O)CC8C(=O)NC(C(=O)N1CCCCC1C(=O)NC(CC(=O)N)C(=O)N8)CC(=O)N)O)Cl)O)CC(=O)N)O)O)O)N)O", "chembl_id": "CHEMBL262777", "phase": "4"},
    {"name": "Levofloxacin",   "smiles": "CC1COC2=C3N1C=C(C(=O)C3=CC(=C2N4CCN(CC4)C)F)C(=O)O", "chembl_id": "CHEMBL33", "phase": "4"},
    {"name": "Trimethoprim",   "smiles": "COC1=CC(=CC(=C1OC)OC)CC2=CN=C(N=C2N)N", "chembl_id": "CHEMBL56", "phase": "4"},
    {"name": "Metronidazole",  "smiles": "CC1=NC=C(N1CCO)[N+](=O)[O-]", "chembl_id": "CHEMBL137", "phase": "4"},
    {"name": "Rifampicin",     "smiles": "CC1C=CC=C(C(=O)NC2=C(C(=C3C(=C2O)C(=C(C4=C3OC(C(C4OC)O)(OC=CC(C(C(C(C(C(C1O)C)O)C)OC(=O)C)C)OC)C)C)O)O)/N=N/N5CCN(CC5)C)C", "chembl_id": "CHEMBL374478", "phase": "4"},
    {"name": "Gentamicin",     "smiles": "CC(C1CCC(C(O1)OC2C(CC(C(C2O)OC3C(C(C(CO3)O)NC)O)N)N)N)NC", "chembl_id": "CHEMBL195892", "phase": "4"},
    {"name": "Ceftriaxone",    "smiles": "CN=C1C=C(CS1)CSC2=NN=C(S2)N.CC(=O)OCC3=C(N4C(C(C4=O)NC(=O)C(=NOC)C5=CSC(=N5)N)SC3)C(=O)O", "chembl_id": "CHEMBL161", "phase": "4"},
    {"name": "Colistin",       "smiles": "CCC(C)CCCC(=O)NC(CCN)C(=O)NC(CC(=O)O)C(=O)NC(CCN)C(=O)NC1CCN(C(=O)C(NC(=O)C(NC(=O)C(NC(=O)C(NC1=O)CCN)CC(=O)O)CCN)CC2=CC=CC=C2)C(C(=O)NC(CCN)C(=O)O)CCN", "chembl_id": "CHEMBL1451", "phase": "4"},
    {"name": "Linezolid",      "smiles": "CC(=O)NCC1CN(C(=O)O1)C2=CC(=C(C=C2)N3CCOCC3)F", "chembl_id": "CHEMBL46", "phase": "4"},
    {"name": "Tigecycline",    "smiles": "CC(C)(C)NCC(=O)NC1C(=O)C(=C(C2(C(=O)C(=C(C3(C2C(C(=C1O)C(=O)N)O)O)O)O)O)O)N(C)C", "chembl_id": "CHEMBL376140", "phase": "4"},
    {"name": "Fosfomycin",     "smiles": "CC1C(O1)P(=O)(O)O", "chembl_id": "CHEMBL1256", "phase": "4"},
    {"name": "Nitrofurantoin", "smiles": "C1C(=O)NC(=O)N1/N=C/C2=CC=C(O2)[N+](=O)[O-]", "chembl_id": "CHEMBL415", "phase": "4"},
    {"name": "Chloramphenicol","smiles": "C(C1C(C(=O)NCC(Cl)Cl)NC1=O)O.[N+](=O)([O-])C1=CC=C(C=C1)C(O)C", "chembl_id": "CHEMBL130", "phase": "4"},
    {"name": "Sulfamethoxazole","smiles": "CC1=CC(=NO1)NS(=O)(=O)C2=CC=C(C=C2)N", "chembl_id": "CHEMBL21", "phase": "4"},
    {"name": "Polymyxin B",    "smiles": "CCC(C)CCCC(=O)NC(CCN)C(=O)NC(CC(=O)O)C(=O)NC(CCN)C(=O)NC1CCN(C(=O)C(CCN)NC(=O)C(CC(=O)O)NC(=O)C(CCN)NC(=O)C(CCN)NC1=O)C(CC2=CC=CC=C2)NC(=O)C(CCN)C(=O)O", "chembl_id": "CHEMBL1232048", "phase": "4"},
]


class DrugLibrary:
    """Manages retrieval and caching of approved drug compound data."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._approved_cache: Optional[list[dict[str, str]]] = None
        self._repurposing_cache: Optional[list[dict[str, str]]] = None
        self._smiles_index: dict[str, str] = {}

    # -- public API -----------------------------------------------------------

    async def fetch_approved_drugs(self, limit: int = 500) -> list[dict[str, str]]:
        """Fetch phase-4 approved drugs from ChEMBL.

        Falls back to hardcoded antibiotics on network failure.
        """
        if self._approved_cache is not None:
            return self._approved_cache

        url = (
            f"{self._settings.chembl_base}/molecule.json"
            f"?max_phase=4"
            f"&molecule_structures__canonical_smiles__isnull=false"
            f"&limit={limit}&format=json"
        )
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
            data = resp.json()
            molecules = data.get("molecules", [])
            results: list[dict[str, str]] = []
            for mol in molecules:
                structs = mol.get("molecule_structures") or {}
                smiles = structs.get("canonical_smiles", "")
                if smiles:
                    entry = {
                        "name": mol.get("pref_name") or mol.get("molecule_chembl_id", ""),
                        "smiles": smiles,
                        "chembl_id": mol.get("molecule_chembl_id", ""),
                        "phase": str(mol.get("max_phase", "")),
                    }
                    results.append(entry)
            self._approved_cache = results if results else _FALLBACK_ANTIBIOTICS
        except Exception as exc:
            logger.warning("ChEMBL fetch failed (%s); using fallback antibiotic set", exc)
            self._approved_cache = _FALLBACK_ANTIBIOTICS

        self._index_smiles(self._approved_cache)
        return self._approved_cache

    async def fetch_drug_repurposing_hub(self) -> list[dict[str, str]]:
        """Download and parse the Broad Drug Repurposing Hub TSV."""
        if self._repurposing_cache is not None:
            return self._repurposing_cache

        url = self._settings.drug_repurposing_hub_url
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
            text = resp.text
            # Skip comment lines starting with '!'
            lines = [ln for ln in text.splitlines() if not ln.startswith("!")]
            reader = csv.DictReader(io.StringIO("\n".join(lines)), delimiter="\t")
            results: list[dict[str, str]] = []
            for row in reader:
                smiles = row.get("smiles", "").strip()
                if smiles:
                    results.append({
                        "name": row.get("pert_iname", row.get("name", "")),
                        "smiles": smiles,
                        "clinical_phase": row.get("clinical_phase", ""),
                        "moa": row.get("moa", ""),
                        "disease_area": row.get("disease_area", ""),
                    })
            self._repurposing_cache = results
        except Exception as exc:
            logger.warning("Repurposing Hub fetch failed (%s); returning empty list", exc)
            self._repurposing_cache = []

        self._index_smiles(self._repurposing_cache)
        return self._repurposing_cache

    def get_drug_smiles(self, drug_name: str) -> Optional[str]:
        """Look up SMILES by drug name (case-insensitive).

        Searches cached approved drugs and repurposing hub data.
        Falls back to the hardcoded antibiotic set.
        """
        key = drug_name.strip().lower()
        if key in self._smiles_index:
            return self._smiles_index[key]
        # Fallback scan of hardcoded list
        for entry in _FALLBACK_ANTIBIOTICS:
            if entry["name"].lower() == key:
                return entry["smiles"]
        return None

    # -- internals ------------------------------------------------------------

    def _index_smiles(self, drugs: list[dict[str, str]]) -> None:
        for entry in drugs:
            name = entry.get("name", "").strip().lower()
            smiles = entry.get("smiles", "")
            if name and smiles:
                self._smiles_index[name] = smiles
