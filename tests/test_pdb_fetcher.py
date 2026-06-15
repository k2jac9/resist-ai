"""Security + correctness tests for PDB/UniProt identifier validation.

The audit hardened PDBFetcher against path traversal and SSRF by strictly
validating identifiers *before* any path join or network call. These tests
lock that in.
"""
import asyncio

import pytest

from src.data.pdb_fetcher import (
    PDBFetcher,
    _validate_pdb_id,
    _validate_uniprot_id,
)

MALICIOUS = [
    "../../etc/passwd",
    "../../../",
    "3SPU/../../secret",
    "169.254.169.254",
    "http://evil.com/x",
    "3SP\x00",
    "3SP U",
    "",
    "   ",
]


class TestPdbIdValidation:
    def test_valid_normalises_to_upper(self):
        assert _validate_pdb_id("3spu") == "3SPU"
        assert _validate_pdb_id("  3SPU  ") == "3SPU"

    @pytest.mark.parametrize("bad", MALICIOUS + ["ABC", "ABCDE"])
    def test_rejects_bad(self, bad):
        with pytest.raises(ValueError, match="Invalid PDB ID"):
            _validate_pdb_id(bad)


class TestUniProtIdValidation:
    def test_valid_normalises_to_upper(self):
        assert _validate_uniprot_id("c7c422") == "C7C422"

    @pytest.mark.parametrize("bad", MALICIOUS + ["SHORT", "WAYTOOLONGID12"])
    def test_rejects_bad(self, bad):
        with pytest.raises(ValueError, match="Invalid UniProt accession"):
            _validate_uniprot_id(bad)


class TestFetcherRejectsBeforeNetwork:
    """A malicious id must raise during validation, never reaching the network."""

    def test_fetch_pdb_rejects(self):
        fetcher = PDBFetcher()
        with pytest.raises(ValueError):
            asyncio.run(fetcher.fetch_pdb("../../etc/passwd"))

    def test_fetch_fasta_rejects(self):
        fetcher = PDBFetcher()
        with pytest.raises(ValueError):
            asyncio.run(fetcher.fetch_fasta("http://169.254.169.254/"))

    def test_get_structure_path_rejects(self):
        fetcher = PDBFetcher()
        with pytest.raises(ValueError):
            asyncio.run(fetcher.get_structure_path("3SP\x00"))
