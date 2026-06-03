"""Tests for PDBFetcher identifier validation.

Identifiers are interpolated into outbound URLs and local file paths, so the
fetcher must reject anything that could enable path traversal or SSRF. Invalid
identifiers are rejected before any network call, so these tests need no I/O.
"""
import asyncio

import pytest

from src.data.pdb_fetcher import PDBFetcher


@pytest.fixture
def fetcher():
    return PDBFetcher()


# Payloads that must never reach the filesystem or an outbound request.
MALICIOUS_IDS = [
    "../../etc/passwd",
    "..%2f..%2fetc",
    "3SPU/../../secret",
    "3SPU/../",
    "@evil.com",
    "localhost:8080",
    "http://169.254.169.254/latest/meta-data",
    "3SPU\x00.pdb",
    "a b",
    "",
    "   ",
    "TOOLONGID12345",
]


@pytest.mark.parametrize("bad_id", MALICIOUS_IDS)
def test_fetch_pdb_rejects_invalid_ids(fetcher, bad_id):
    assert asyncio.run(fetcher.fetch_pdb(bad_id)) is None


@pytest.mark.parametrize("bad_id", MALICIOUS_IDS)
def test_get_structure_path_rejects_invalid_ids(fetcher, bad_id):
    assert asyncio.run(fetcher.get_structure_path(bad_id)) is None


@pytest.mark.parametrize("bad_id", MALICIOUS_IDS)
def test_fetch_fasta_rejects_invalid_ids(fetcher, bad_id):
    assert asyncio.run(fetcher.fetch_fasta(bad_id)) is None


def test_valid_pdb_id_passes_validation(fetcher, monkeypatch):
    """A well-formed PDB ID is accepted (network call is stubbed out)."""
    calls = {}

    async def fake_fetch(self, pdb_id):
        calls["pdb_id"] = pdb_id
        return None

    monkeypatch.setattr(PDBFetcher, "fetch_pdb", fake_fetch)
    asyncio.run(fetcher.get_structure_path("3spu"))
    assert calls["pdb_id"] == "3SPU"  # normalized to upper-case, validated


@pytest.mark.parametrize("good_id", ["3SPU", "1ABC", "PDB_00001ABC"])
def test_extended_and_classic_pdb_ids_accepted(good_id):
    from src.data.pdb_fetcher import _PDB_ID_RE

    assert _PDB_ID_RE.match(good_id)


@pytest.mark.parametrize("good_id", ["C7C422", "P0DTC2", "A0A0A0A0A0"])
def test_valid_uniprot_accessions_accepted(good_id):
    from src.data.pdb_fetcher import _UNIPROT_ID_RE

    assert _UNIPROT_ID_RE.match(good_id)
