"""Target protein representation for the ResistAI Pipeline SDK.

Supports construction from raw amino acid sequences, UniProt accessions,
or PDB identifiers.  Fetching from remote databases is done synchronously
via httpx so the SDK stays simple to use in scripts and notebooks.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)

_UNIPROT_BASE = "https://rest.uniprot.org/uniprotkb"
_PDB_FASTA_BASE = "https://www.rcsb.org/fasta/entry"
_PDB_FILE_BASE = "https://files.rcsb.org/download"
_TIMEOUT = 30.0

# Identifier formats, enforced before any value is interpolated into a URL.
_PDB_ID_RE = re.compile(r"^[A-Za-z0-9]{4}$")
_UNIPROT_ID_RE = re.compile(r"^[A-Za-z0-9]{6,10}$")


def _parse_fasta(text: str) -> str:
    """Extract the first sequence from a FASTA string."""
    lines: list[str] = []
    for line in text.splitlines():
        if line.startswith(">"):
            if lines:
                break  # stop at second header
            continue
        lines.append(line.strip())
    return "".join(lines)


@dataclass
class Target:
    """A protein target for the drug-discovery pipeline.

    Attributes:
        sequence:   Amino acid sequence (single-letter codes).
        name:       Human-readable label (e.g. ``"NDM-1"``).
        source:     How the target was created (``"sequence"``, ``"uniprot"``, ``"pdb"``).
        source_id:  UniProt accession or PDB ID when applicable.
        pdb_string: Raw PDB file contents, populated by ``from_pdb`` or after folding.
        metadata:   Arbitrary extra data attached to this target.
    """

    sequence: str = ""
    name: str = ""
    source: str = "sequence"
    source_id: str = ""
    pdb_string: str = ""
    metadata: dict = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Constructors
    # ------------------------------------------------------------------

    @classmethod
    def from_sequence(cls, sequence: str, *, name: str = "") -> Target:
        """Create a target directly from an amino acid sequence.

        Args:
            sequence: Amino acid string (whitespace is stripped).
            name:     Optional label for this target.
        """
        cleaned = "".join(sequence.split()).upper()
        if not cleaned:
            raise ValueError("sequence must not be empty")
        return cls(
            sequence=cleaned,
            name=name or f"seq_{len(cleaned)}aa",
            source="sequence",
        )

    @classmethod
    def from_uniprot(cls, accession: str, *, name: str = "") -> Target:
        """Fetch a protein sequence from the UniProt REST API.

        Args:
            accession: UniProt accession (e.g. ``"C7C422"``).
            name:      Optional label; defaults to the accession.

        Raises:
            RuntimeError: If the fetch fails after retries.
        """
        accession = accession.strip().upper()
        if not _UNIPROT_ID_RE.match(accession):
            raise ValueError(f"Invalid UniProt accession: {accession!r}")
        url = f"{_UNIPROT_BASE}/{accession}.fasta"
        try:
            resp = httpx.get(url, timeout=_TIMEOUT, follow_redirects=True)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise RuntimeError(
                f"Failed to fetch UniProt {accession}: {exc}"
            ) from exc

        seq = _parse_fasta(resp.text)
        if not seq:
            raise RuntimeError(f"No sequence found in UniProt response for {accession}")

        label = name or accession
        logger.info("Fetched %s from UniProt (%d aa)", label, len(seq))
        return cls(
            sequence=seq,
            name=label,
            source="uniprot",
            source_id=accession,
            metadata={"fasta_header": resp.text.split("\n", 1)[0]},
        )

    @classmethod
    def from_pdb(cls, pdb_id: str, *, name: str = "") -> Target:
        """Fetch a protein from the RCSB PDB (sequence + structure).

        Downloads both the FASTA sequence and the PDB coordinate file.

        Args:
            pdb_id: Four-character PDB identifier (e.g. ``"3SPU"``).
            name:   Optional label; defaults to the PDB ID.

        Raises:
            RuntimeError: If the fetch fails.
        """
        pdb_id = pdb_id.strip().upper()
        if not _PDB_ID_RE.match(pdb_id):
            raise ValueError(f"Invalid PDB id: {pdb_id!r}")

        # Fetch FASTA for the sequence
        fasta_url = f"{_PDB_FASTA_BASE}/{pdb_id}"
        try:
            fasta_resp = httpx.get(fasta_url, timeout=_TIMEOUT, follow_redirects=True)
            fasta_resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Failed to fetch PDB FASTA {pdb_id}: {exc}") from exc

        seq = _parse_fasta(fasta_resp.text)
        if not seq:
            raise RuntimeError(f"No sequence found in PDB FASTA for {pdb_id}")

        # Fetch PDB coordinate file
        pdb_url = f"{_PDB_FILE_BASE}/{pdb_id}.pdb"
        pdb_string = ""
        try:
            pdb_resp = httpx.get(pdb_url, timeout=_TIMEOUT, follow_redirects=True)
            pdb_resp.raise_for_status()
            pdb_string = pdb_resp.text
        except httpx.HTTPError:
            logger.warning("Could not fetch PDB file for %s; structure unavailable", pdb_id)

        label = name or pdb_id
        logger.info("Fetched %s from PDB (%d aa, structure=%s)", label, len(seq), bool(pdb_string))
        return cls(
            sequence=seq,
            name=label,
            source="pdb",
            source_id=pdb_id,
            pdb_string=pdb_string,
            metadata={"fasta_header": fasta_resp.text.split("\n", 1)[0]},
        )

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @property
    def has_structure(self) -> bool:
        """Whether a 3D structure (PDB string) is available."""
        return bool(self.pdb_string and len(self.pdb_string) > 100)

    @property
    def length(self) -> int:
        """Number of amino acids in the sequence."""
        return len(self.sequence)

    def __repr__(self) -> str:
        struct = "with structure" if self.has_structure else "no structure"
        return f"Target(name={self.name!r}, {self.length}aa, {struct}, source={self.source})"
