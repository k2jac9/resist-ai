"""Tests for src/models/nim_client.py -- offline-safe, no API keys required."""
import os
from unittest.mock import patch

import pytest

from src.models.nim_client import (
    ENDPOINTS,
    Boltz2Result,
    ESMFoldResult,
    MolMIMResult,
    NIMClient,
)


# -- NIMClient init ------------------------------------------------------------

class TestNIMClientInit:
    def test_no_key_means_unavailable(self):
        with patch.dict(os.environ, {}, clear=True):
            # Also prevent reading from .env file
            with patch("src.models.nim.base._get_api_key", return_value=""):
                client = NIMClient(api_key="")
                assert client.available is False

    def test_with_key_is_available(self):
        client = NIMClient(api_key="nvapi-test-key")
        assert client.available is True

    def test_post_raises_without_key(self):
        with patch("src.models.nim.base._get_api_key", return_value=""):
            client = NIMClient(api_key="")
            with pytest.raises(RuntimeError, match="not available"):
                client._post("esmfold", {})


# -- ENDPOINTS dict ------------------------------------------------------------

class TestEndpoints:
    def test_all_seven_endpoints_present(self):
        expected = {"esmfold", "evo2", "boltz2", "molmim", "rfdiffusion", "proteinmpnn", "diffdock"}
        assert set(ENDPOINTS.keys()) == expected

    def test_endpoints_are_urls(self):
        for name, url in ENDPOINTS.items():
            assert url.startswith("https://"), f"{name} URL does not start with https://"


# -- Result dataclasses --------------------------------------------------------

class TestResultDataclasses:
    def test_esmfold_defaults(self):
        r = ESMFoldResult()
        assert r.pdb_string == ""
        assert r.sequence_length == 0
        assert r.success is False
        assert r.elapsed_ms == 0.0

    def test_boltz2_defaults(self):
        r = Boltz2Result()
        assert r.confidence_score == 0.0
        assert r.ptm_score == 0.0
        assert r.iptm_score == 0.0
        assert r.ligand_iptm_score == 0.0
        assert r.complex_plddt == 0.0
        assert r.structure_cif == ""
        assert r.success is False
        assert r.raw_affinities == {}

    def test_molmim_defaults(self):
        r = MolMIMResult()
        assert r.molecules == []
        assert r.score_type == ""
        assert r.num_generated == 0
        assert r.success is False

    def test_esmfold_with_values(self):
        r = ESMFoldResult(pdb_string="ATOM...", sequence_length=42, success=True, elapsed_ms=123.4)
        assert r.success is True
        assert r.sequence_length == 42
        assert r.elapsed_ms == 123.4
