"""PDB structure and FASTA sequence fetcher.

Downloads macromolecular structures from RCSB PDB and protein sequences
from the UniProt REST API, caching files locally under data/structures/.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional

import httpx

from src.utils.config import get_settings

logger = logging.getLogger(__name__)

# PDB IDs are 4 alphanumeric chars; UniProt accessions are 6-10 alphanumerics.
_PDB_ID_RE = re.compile(r"^[A-Z0-9]{4}$")
_UNIPROT_ID_RE = re.compile(r"^[A-Z0-9]{6,10}$")


def _validate_pdb_id(pdb_id: str) -> str:
    """Normalise and strictly validate a PDB identifier (prevents traversal/SSRF)."""
    pdb_id = pdb_id.strip().upper()
    if not _PDB_ID_RE.match(pdb_id):
        raise ValueError(f"Invalid PDB ID: {pdb_id!r}")
    return pdb_id


def _validate_uniprot_id(uniprot_id: str) -> str:
    """Normalise and strictly validate a UniProt accession."""
    uniprot_id = uniprot_id.strip().upper()
    if not _UNIPROT_ID_RE.match(uniprot_id):
        raise ValueError(f"Invalid UniProt accession: {uniprot_id!r}")
    return uniprot_id


class PDBFetcher:
    """Fetches and caches PDB structures and FASTA sequences."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._structures_dir: Path = self._settings.structures_dir

    # -- public API -----------------------------------------------------------

    async def fetch_pdb(self, pdb_id: str) -> Optional[Path]:
        """Download a PDB file from RCSB and save locally.

        Args:
            pdb_id: Four-character PDB identifier (e.g. ``"3SPU"``).

        Returns:
            Path to the downloaded file, or ``None`` on failure.
        """
        pdb_id = _validate_pdb_id(pdb_id)
        dest = self._structures_dir / f"{pdb_id}.pdb"
        if dest.exists():
            logger.debug("PDB %s already cached at %s", pdb_id, dest)
            return dest

        url = f"{self._settings.pdb_base}/{pdb_id}.pdb"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
            dest.write_text(resp.text)
            logger.info("Downloaded PDB %s -> %s", pdb_id, dest)
            return dest
        except Exception as exc:
            logger.error("Failed to fetch PDB %s: %s", pdb_id, exc)
            return None

    async def fetch_fasta(self, uniprot_id: str) -> Optional[Path]:
        """Download a FASTA file from UniProt REST API.

        Args:
            uniprot_id: UniProt accession (e.g. ``"C7C422"``).

        Returns:
            Path to the downloaded FASTA file, or ``None`` on failure.
        """
        uniprot_id = _validate_uniprot_id(uniprot_id)
        dest = self._structures_dir / f"{uniprot_id}.fasta"
        if dest.exists():
            logger.debug("FASTA %s already cached at %s", uniprot_id, dest)
            return dest

        url = f"{self._settings.uniprot_base}/uniprotkb/{uniprot_id}.fasta"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
            dest.write_text(resp.text)
            logger.info("Downloaded FASTA %s -> %s", uniprot_id, dest)
            return dest
        except Exception as exc:
            logger.error("Failed to fetch FASTA %s: %s", uniprot_id, exc)
            return None

    async def get_structure_path(self, pdb_id: str) -> Optional[Path]:
        """Return local path to a PDB file, fetching if not cached.

        Args:
            pdb_id: Four-character PDB identifier.

        Returns:
            Path to the PDB file, or ``None`` if download fails.
        """
        pdb_id = _validate_pdb_id(pdb_id)
        dest = self._structures_dir / f"{pdb_id}.pdb"
        if dest.exists():
            return dest
        return await self.fetch_pdb(pdb_id)

    def list_cached(self) -> list[str]:
        """Return PDB IDs of all locally cached structure files."""
        return [
            p.stem
            for p in self._structures_dir.glob("*.pdb")
        ]
