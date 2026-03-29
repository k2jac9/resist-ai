"""MolMIM novel molecule generation mixin."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class MolMIMResult:
    """Novel molecule generation result."""
    molecules: list[dict] = field(default_factory=list)
    score_type: str = ""
    num_generated: int = 0
    success: bool = False


class MolMIMMixin:
    """Mixin providing generate_molecules() for NIMClient."""

    def generate_molecules(
        self,
        seed_smiles: str,
        num_molecules: int = 5,
        property_name: str = "QED",
        minimize: bool = False,
        min_similarity: float = 0.3,
        algorithm: str = "CMA-ES",
    ) -> MolMIMResult:
        """Generate novel optimized molecules from a seed SMILES using MolMIM.

        Args:
            seed_smiles: Starting molecule SMILES.
            num_molecules: Number of molecules to generate.
            property_name: Property to optimize (QED, logP, etc.).
            minimize: Whether to minimize the property.
            min_similarity: Minimum Tanimoto similarity to seed.
            algorithm: Optimization algorithm (CMA-ES, etc.).

        Returns:
            MolMIMResult with generated molecules and scores.
        """
        payload = {
            "smi": seed_smiles,
            "num_molecules": num_molecules,
            "algorithm": algorithm,
            "property_name": property_name,
            "minimize": minimize,
            "min_similarity": min_similarity,
        }
        try:
            data = self._post("molmim", payload)
            if isinstance(data, str):
                return MolMIMResult()

            raw_mols = data.get("molecules", "[]")
            if isinstance(raw_mols, str):
                molecules = json.loads(raw_mols)
            else:
                molecules = raw_mols

            return MolMIMResult(
                molecules=molecules,
                score_type=data.get("score_type", property_name),
                num_generated=len(molecules),
                success=len(molecules) > 0,
            )
        except Exception as exc:
            logger.error("MolMIM error: %s", exc)
            return MolMIMResult()
