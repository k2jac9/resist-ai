"""Pathogen data manager for ESKAPE organisms.

Loads pathogen metadata from the central settings.yaml and exposes
convenient lookup methods for targets, PDB codes, UniProt IDs, and
WHO priority levels.
"""

from __future__ import annotations

from typing import Any, Optional

from src.utils.config import get_settings


class PathogenManager:
    """Provides access to ESKAPE pathogen data loaded from configuration."""

    def __init__(self) -> None:
        self._pathogens: dict[str, Any] = get_settings().eskape_pathogens

    # -- public API -----------------------------------------------------------

    def list_pathogens(self) -> list[str]:
        """Return a sorted list of available pathogen identifiers."""
        return sorted(self._pathogens.keys())

    def get_pathogen(self, name: str) -> Optional[dict[str, Any]]:
        """Return full pathogen info by identifier.

        Args:
            name: Pathogen key, e.g. ``"acinetobacter_baumannii"``.

        Returns:
            Dict with keys: name, who_priority, resistance, proteome_id,
            key_targets.  ``None`` if the pathogen is not found.
        """
        return self._pathogens.get(name)

    def get_target(
        self, pathogen: str, target_name: str
    ) -> Optional[dict[str, Any]]:
        """Return a specific drug-target entry for a pathogen.

        Args:
            pathogen: Pathogen key.
            target_name: Target name, e.g. ``"NDM-1"``.

        Returns:
            Dict with keys like pdb, uniprot, function.
            ``None`` if not found.
        """
        pathogen_data = self._pathogens.get(pathogen)
        if pathogen_data is None:
            return None
        for target in pathogen_data.get("key_targets", []):
            if target["name"] == target_name:
                return target
        return None

    def get_pdb_codes(self, pathogen: str) -> list[str]:
        """Return all PDB codes for a given pathogen's targets."""
        pathogen_data = self._pathogens.get(pathogen)
        if pathogen_data is None:
            return []
        return [
            t["pdb"]
            for t in pathogen_data.get("key_targets", [])
            if "pdb" in t
        ]

    def get_uniprot_ids(self, pathogen: str) -> list[str]:
        """Return all UniProt IDs for a given pathogen's targets."""
        pathogen_data = self._pathogens.get(pathogen)
        if pathogen_data is None:
            return []
        return [
            t["uniprot"]
            for t in pathogen_data.get("key_targets", [])
            if "uniprot" in t
        ]

    def get_who_priority(self, pathogen: str) -> Optional[str]:
        """Return the WHO priority level for a pathogen."""
        pathogen_data = self._pathogens.get(pathogen)
        if pathogen_data is None:
            return None
        return pathogen_data.get("who_priority")

    def get_critical_pathogens(self) -> list[str]:
        """Return pathogen keys whose WHO priority is 'critical'."""
        return [
            key
            for key, data in self._pathogens.items()
            if data.get("who_priority") == "critical"
        ]
