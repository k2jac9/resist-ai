"""NVIDIA NIM Biology API client — modular package.

Re-exports NIMClient and all result dataclasses for convenient imports:
    from src.models.nim import NIMClient, ESMFoldResult, Boltz2Result
"""
from .base import NIMBase, ENDPOINTS, NIM_BASE, _get_api_key
from .esmfold import ESMFoldMixin, ESMFoldResult
from .evo2 import Evo2Mixin, Evo2Result
from .boltz2 import Boltz2Mixin, Boltz2Result
from .molmim import MolMIMMixin, MolMIMResult
from .diffdock import DiffDockMixin, DiffDockResult
from .rfdiffusion import RFdiffusionMixin, RFdiffusionResult
from .proteinmpnn import ProteinMPNNMixin, ProteinMPNNResult


class NIMClient(
    NIMBase,
    ESMFoldMixin,
    Evo2Mixin,
    Boltz2Mixin,
    MolMIMMixin,
    DiffDockMixin,
    RFdiffusionMixin,
    ProteinMPNNMixin,
):
    """Unified NVIDIA NIM Biology API client."""
    pass


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
    "_get_api_key",
]
