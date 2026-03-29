"""RFdiffusion de novo protein backbone design mixin."""
from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RFdiffusionResult:
    """De novo protein backbone design result."""
    pdb_string: str = ""
    num_residues: int = 0
    elapsed_ms: float = 0.0
    success: bool = False


class RFdiffusionMixin:
    """Mixin providing design_binder() for NIMClient."""

    def design_binder(
        self,
        target_pdb: str,
        contigs: str = "10-40/A1-60/10-40",
    ) -> RFdiffusionResult:
        """Design a novel protein backbone that binds to a target structure.

        Args:
            target_pdb: PDB structure string of the target protein.
            contigs: Contig specification for RFdiffusion.

        Returns:
            RFdiffusionResult with designed backbone PDB.
        """
        try:
            data = self._post("rfdiffusion", {
                "contigs": contigs,
                "input_pdb": target_pdb,
            }, timeout=180)
            if isinstance(data, str):
                return RFdiffusionResult(pdb_string=data, success=bool(data))

            pdb = data.get("output_pdb", data.get("pdb", ""))
            return RFdiffusionResult(
                pdb_string=pdb,
                num_residues=pdb.count("\nATOM") if pdb else 0,
                elapsed_ms=data.get("_elapsed_ms", data.get("elapsed_ms", 0)),
                success=bool(pdb),
            )
        except Exception as exc:
            logger.error("RFdiffusion error: %s", exc)
            return RFdiffusionResult()
