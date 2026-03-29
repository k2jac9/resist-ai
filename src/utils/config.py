"""Configuration loader for AMR-AI platform.

Loads settings from config/settings.yaml and environment variables via python-dotenv.
Provides typed, singleton access to all configuration values.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

import yaml
from dotenv import load_dotenv

# Project root: two levels up from src/utils/
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class _Settings:
    """Singleton configuration container with typed accessors."""

    _instance: Optional[_Settings] = None
    _loaded: bool = False

    def __new__(cls) -> _Settings:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if self._loaded:
            return
        load_dotenv(PROJECT_ROOT / ".env")
        config_path = PROJECT_ROOT / "config" / "settings.yaml"
        with open(config_path, "r") as fh:
            self._data: dict[str, Any] = yaml.safe_load(fh)
        self._loaded = True

    # -- raw access -----------------------------------------------------------

    def get(self, dotted_key: str, default: Any = None) -> Any:
        """Retrieve a nested value using dot-separated keys.

        Example: settings.get("nebius.models.boltz2")
        """
        keys = dotted_key.split(".")
        node: Any = self._data
        for key in keys:
            if isinstance(node, dict) and key in node:
                node = node[key]
            else:
                return default
        return node

    # -- app ------------------------------------------------------------------

    @property
    def app_name(self) -> str:
        return self._data["app"]["name"]

    @property
    def app_version(self) -> str:
        return self._data["app"]["version"]

    # -- Nebius AI Studio -----------------------------------------------------

    @property
    def nebius_api_key(self) -> str:
        key = os.getenv("NEBIUS_API_KEY", "")
        if not key:
            raise EnvironmentError("NEBIUS_API_KEY is not set")
        return key

    @property
    def nebius_base_url(self) -> str:
        return self._data["nebius"]["base_url"]

    @property
    def nebius_models(self) -> dict[str, str]:
        return self._data["nebius"]["models"]

    # -- ESM-2 ----------------------------------------------------------------

    @property
    def esm2_model_name(self) -> str:
        return self._data["esm2"]["model_name"]

    @property
    def esm2_embedding_dim(self) -> int:
        return int(self._data["esm2"]["embedding_dim"])

    # -- target discovery -----------------------------------------------------

    @property
    def default_pathogen(self) -> str:
        return self._data["target_discovery"]["default_pathogen"]

    @property
    def card_url(self) -> str:
        return self._data["target_discovery"]["databases"]["card_url"]

    @property
    def uniprot_base(self) -> str:
        return self._data["target_discovery"]["databases"]["uniprot_base"]

    @property
    def pdb_base(self) -> str:
        return self._data["target_discovery"]["databases"]["pdb_base"]

    # -- drug screening -------------------------------------------------------

    @property
    def max_compounds(self) -> int:
        return int(self._data["drug_screening"]["max_compounds"])

    @property
    def binding_threshold(self) -> float:
        return float(self._data["drug_screening"]["binding_threshold"])

    @property
    def chembl_base(self) -> str:
        return self._data["drug_screening"]["databases"]["chembl_base"]

    @property
    def drug_repurposing_hub_url(self) -> str:
        return self._data["drug_screening"]["databases"]["drug_repurposing_hub"]

    # -- safety prediction ----------------------------------------------------

    @property
    def off_target_similarity_threshold(self) -> float:
        return float(self._data["safety_prediction"]["off_target_similarity_threshold"])

    @property
    def toxicity_endpoints(self) -> list[str]:
        return self._data["safety_prediction"]["toxicity_endpoints"]

    # -- ESKAPE pathogens -----------------------------------------------------

    @property
    def eskape_pathogens(self) -> dict[str, Any]:
        return self._data["eskape_pathogens"]

    # -- data directories -----------------------------------------------------

    @property
    def structures_dir(self) -> Path:
        path = PROJECT_ROOT / "data" / "structures"
        path.mkdir(parents=True, exist_ok=True)
        return path


def get_settings() -> _Settings:
    """Return the singleton Settings instance."""
    return _Settings()
