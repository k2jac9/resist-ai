"""Backwards compatibility -- import from src.models.nim instead."""
from src.models.nim import (  # noqa: F401
    NIMClient,
    NIMBase,
    ENDPOINTS,
    NIM_BASE,
    ESMFoldResult,
    Evo2Result,
    Boltz2Result,
    MolMIMResult,
    DiffDockResult,
    RFdiffusionResult,
    ProteinMPNNResult,
    _get_api_key,
)

__all__ = [
    "NIMClient",
    "NIMBase",
    "ENDPOINTS",
    "NIM_BASE",
    "ESMFoldResult",
    "Evo2Result",
    "Boltz2Result",
    "MolMIMResult",
    "DiffDockResult",
    "RFdiffusionResult",
    "ProteinMPNNResult",
]
