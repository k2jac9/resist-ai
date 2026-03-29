"""DiffDock molecular docking mixin."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class DiffDockResult:
    """Molecular docking result."""
    ligand_positions: list[str] = field(default_factory=list)
    position_confidence: list[float] = field(default_factory=list)
    num_poses: int = 0
    protein_pdb: str = ""
    success: bool = False


class DiffDockMixin:
    """Mixin providing dock_molecule() for NIMClient."""

    def dock_molecule(
        self,
        protein_pdb: str,
        ligand_smiles: str,
        num_poses: int = 5,
        time_divisions: int = 20,
        num_steps: int = 18,
    ) -> DiffDockResult:
        """Predict 3D binding pose of a ligand in a protein using DiffDock.

        Args:
            protein_pdb: PDB structure string of the target protein.
            ligand_smiles: SMILES string of the ligand.
            num_poses: Number of docking poses to generate.
            time_divisions: Diffusion time divisions.
            num_steps: Number of diffusion steps.

        Returns:
            DiffDockResult with docking poses and confidence scores.
        """
        try:
            data = self._post("diffdock", {
                "protein": protein_pdb,
                "ligand": ligand_smiles,
                "ligand_file_type": "txt",
                "num_poses": num_poses,
                "time_divisions": time_divisions,
                "num_steps": num_steps,
            }, timeout=180)
            if isinstance(data, str):
                return DiffDockResult()

            positions = data.get("ligand_positions", [])
            confidence = data.get("position_confidence", [])
            flat_pos = []
            for p in positions:
                if isinstance(p, list):
                    flat_pos.extend(p)
                else:
                    flat_pos.append(p)

            return DiffDockResult(
                ligand_positions=flat_pos,
                position_confidence=confidence if isinstance(confidence, list) else [confidence],
                num_poses=len(flat_pos),
                protein_pdb=data.get("protein", ""),
                success=len(flat_pos) > 0,
            )
        except Exception as exc:
            logger.error("DiffDock error: %s", exc)
            return DiffDockResult()
