"""ESMFold protein structure prediction mixin."""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass

import requests

from .base import ENDPOINTS

logger = logging.getLogger(__name__)


@dataclass
class ESMFoldResult:
    """Protein structure prediction result."""
    pdb_string: str = ""
    sequence_length: int = 0
    success: bool = False
    elapsed_ms: float = 0.0


class ESMFoldMixin:
    """Mixin providing fold_protein() for NIMClient."""

    def fold_protein(self, sequence: str) -> ESMFoldResult:
        """Predict 3D structure of a protein from its amino acid sequence.

        Args:
            sequence: Amino acid sequence (e.g. 'MELPNIMH...').

        Returns:
            ESMFoldResult with PDB structure string.
        """
        try:
            t0 = time.time()
            resp = requests.post(
                ENDPOINTS["esmfold"],
                headers=self._headers(),
                json={"sequence": sequence},
                timeout=self._timeout,
            )
            elapsed = (time.time() - t0) * 1000

            if resp.status_code != 200:
                logger.error("ESMFold failed: %d %s", resp.status_code, resp.text[:200])
                return ESMFoldResult()

            try:
                data = resp.json()
                if isinstance(data, dict):
                    pdbs = data.get("pdbs") or []
                    pdb = pdbs[0] if pdbs else data.get("pdb_string", "")
                else:
                    pdb = ""
            except (json.JSONDecodeError, ValueError):
                pdb = resp.text

            return ESMFoldResult(
                pdb_string=pdb,
                sequence_length=len(sequence),
                success=bool(pdb and len(pdb) > 100),
                elapsed_ms=elapsed,
            )
        except Exception as exc:
            logger.error("ESMFold error: %s", exc)
            return ESMFoldResult()
