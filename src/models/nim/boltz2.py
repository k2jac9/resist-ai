"""Boltz-2 response parser: preserve observed metrics, reject malformed responses."""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Boltz2Result:
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
    # Legacy numeric defaults are not observations. Consumers must honor this list.
    observed_fields: list[str] = field(default_factory=list)
    error_code: str = ""


class Boltz2Mixin:
    """Co-folding client. Structural confidence is not measured affinity."""

    def predict_binding(self, protein_sequence: str, ligand_smiles: str) -> Boltz2Result:
        payload = {"polymers": [{"molecule_type": "protein", "sequence": protein_sequence}],
                   "ligands": [{"smiles": ligand_smiles}]}
        try:
            data = self._post("boltz2", payload, timeout=180)
            if not isinstance(data, dict) or data.get("error"):
                raise ValueError("invalid_response")
            fields = (
                ("confidence_scores", "confidence_score", 1),
                ("ptm_scores", "ptm_score", 1),
                ("iptm_scores", "iptm_score", 1),
                ("ligand_iptm_scores", "ligand_iptm_score", 1),
                ("complex_plddt_scores", "complex_plddt", 100),
                ("complex_iplddt_scores", "complex_iplddt", 100),
            )
            metrics = {}
            for source, target, ceiling in fields:
                if source not in data:
                    continue
                values = data[source]
                if not isinstance(values, list) or not values or len(values) > 100:
                    raise ValueError("invalid_metric")
                if any(isinstance(v, bool) or not isinstance(v, (int, float))
                       or not math.isfinite(v) or not 0 <= v <= ceiling for v in values):
                    raise ValueError("invalid_metric")
                metrics[target] = float(values[0])
            if "confidence_score" not in metrics:
                raise ValueError("missing_confidence")
            files = data.get("output_files", [])
            if not isinstance(files, list):
                raise ValueError("invalid_structure")
            cif = ""
            if files:
                if not isinstance(files[0], dict) or not isinstance(files[0].get("content", ""), str):
                    raise ValueError("invalid_structure")
                cif = files[0].get("content", "")
            affinities = data.get("affinities", {})
            if not isinstance(affinities, dict):
                raise ValueError("invalid_affinities")
            elapsed = data.get("_elapsed_ms", 0)
            if isinstance(elapsed, bool) or not isinstance(elapsed, (int, float)) or not math.isfinite(elapsed) or elapsed < 0:
                raise ValueError("invalid_elapsed")
            return Boltz2Result(**metrics, structure_cif=cif, elapsed_ms=float(elapsed),
                                success=True, raw_affinities=affinities,
                                observed_fields=list(metrics))
        except Exception as exc:
            # Provider exception messages can contain private request/response data.
            logger.warning("Boltz-2 response unavailable (%s)", type(exc).__name__)
            return Boltz2Result(error_code="provider_or_response_error")
