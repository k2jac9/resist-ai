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

# Identifiers are interpolated into outbound URLs and local file paths, so they
# must be validated to prevent path traversal and SSRF. PDB IDs are 4-char
# alphanumeric (with an extended ``pdb_xxxxxxxx`` form); UniProt accessions are
# 6 or 10 alphanumeric characters.
_PDB_ID_RE = re.compile(r"^(?:[A-Z0-9]{4}|PDB_[A-Z0-9]{8})$")
_UNIPROT_ID_RE = re.compile(r"^[A-Z0-9]{6,10}$")


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
        pdb_id = pdb_id.strip().upper()
        if not _PDB_ID_RE.match(pdb_id):
            logger.error("Rejected invalid PDB identifier: %r", pdb_id)
            return None
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
        uniprot_id = uniprot_id.strip().upper()
        if not _UNIPROT_ID_RE.match(uniprot_id):
            logger.error("Rejected invalid UniProt accession: %r", uniprot_id)
            return None
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
        pdb_id = pdb_id.strip().upper()
        if not _PDB_ID_RE.match(pdb_id):
            logger.error("Rejected invalid PDB identifier: %r", pdb_id)
            return None
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
