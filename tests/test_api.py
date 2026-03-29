"""Tests for the ResistAI FastAPI server -- uses TestClient, no live NIM calls."""
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.api.server import app


@pytest.fixture
def client():
    """Create a FastAPI TestClient with NIM mocked as unavailable."""
    mock_nim = MagicMock()
    mock_nim.available = False
    mock_nim.health_check.return_value = {}
    with patch("src.api.server._get_nim", return_value=mock_nim):
        with patch("src.api.server._nim_client", mock_nim):
            yield TestClient(app, raise_server_exceptions=False)


# -- Health endpoint -----------------------------------------------------------

class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        resp = client.get("/v1/health")
        assert resp.status_code == 200
        body = resp.json()
        assert "success" in body


# -- Models endpoint -----------------------------------------------------------

class TestModelsEndpoint:
    def test_models_returns_200(self, client):
        resp = client.get("/v1/models")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert "data" in body
        assert body["data"]["model_count"] == 7
        assert len(body["data"]["models"]) == 7

    def test_models_lists_all_names(self, client):
        resp = client.get("/v1/models")
        names = {m["name"] for m in resp.json()["data"]["models"]}
        expected = {"esmfold", "evo2", "boltz2", "molmim", "rfdiffusion", "proteinmpnn", "diffdock"}
        assert names == expected


# -- Binding request validation ------------------------------------------------

class TestBindingValidation:
    def test_missing_fields_returns_422(self, client):
        resp = client.post("/v1/predict/binding", json={})
        assert resp.status_code == 422

    def test_short_sequence_returns_422(self, client):
        resp = client.post("/v1/predict/binding", json={
            "protein_sequence": "SHORT",
            "ligand_smiles": "CCO",
        })
        assert resp.status_code == 422

    def test_missing_smiles_returns_422(self, client):
        resp = client.post("/v1/predict/binding", json={
            "protein_sequence": "MELPNIMHPVAKLSTALAAALMLSGCMPGEIRPTIGQQMETG",
        })
        assert resp.status_code == 422


# -- Structure request validation ----------------------------------------------

class TestStructureValidation:
    def test_missing_sequence_returns_422(self, client):
        resp = client.post("/v1/predict/structure", json={})
        assert resp.status_code == 422

    def test_short_sequence_returns_422(self, client):
        resp = client.post("/v1/predict/structure", json={"sequence": "ABC"})
        assert resp.status_code == 422


# -- Generate request validation -----------------------------------------------

class TestGenerateValidation:
    def test_missing_seed_returns_422(self, client):
        resp = client.post("/v1/generate/molecules", json={})
        assert resp.status_code == 422

    def test_invalid_num_molecules_returns_422(self, client):
        resp = client.post("/v1/generate/molecules", json={
            "seed_smiles": "CCO",
            "num_molecules": 0,
        })
        assert resp.status_code == 422
