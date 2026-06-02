"""Tests for the fail-closed API authentication behaviour.

Each test reloads ``src.api.server`` with a specific environment because the
module resolves auth configuration at import time.
"""
import importlib
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


def _load_app(monkeypatch, **env):
    """Reload the server module with the given RESISTAI_* env and return the app."""
    for key in ("RESISTAI_API_KEY", "RESISTAI_ALLOW_NO_AUTH", "RESISTAI_CORS_ORIGINS"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    import src.api.server as server
    return importlib.reload(server)


def _client(server):
    mock_nim = MagicMock()
    mock_nim.available = False
    mock_nim.health_check.return_value = {}
    # Patch on the freshly reloaded module object.
    p = patch.object(server, "_get_nim", return_value=mock_nim)
    p.start()
    return TestClient(server.app, raise_server_exceptions=False), p


def test_no_key_and_no_optout_fails_closed(monkeypatch):
    """With no key configured and no opt-out, protected endpoints return 503."""
    server = _load_app(monkeypatch)  # neither var set
    client, p = _client(server)
    try:
        resp = client.post("/v1/predict/binding", json={
            "protein_sequence": "MELPNIMHPVAKLSTALAAALMLSGCMPGEIRPTIGQQMETG",
            "ligand_smiles": "CCO",
        })
        assert resp.status_code == 503
    finally:
        p.stop()


def test_configured_key_rejects_missing_and_wrong_key(monkeypatch):
    server = _load_app(monkeypatch, RESISTAI_API_KEY="s3cret")
    client, p = _client(server)
    try:
        body = {
            "protein_sequence": "MELPNIMHPVAKLSTALAAALMLSGCMPGEIRPTIGQQMETG",
            "ligand_smiles": "CCO",
        }
        # Missing key
        assert client.post("/v1/predict/binding", json=body).status_code == 401
        # Wrong key
        assert client.post(
            "/v1/predict/binding", json=body, headers={"X-API-Key": "nope"}
        ).status_code == 401
        # Correct key passes auth (503 because NIM is mocked unavailable)
        assert client.post(
            "/v1/predict/binding", json=body, headers={"X-API-Key": "s3cret"}
        ).status_code == 503
    finally:
        p.stop()


def test_allow_no_auth_opt_out(monkeypatch):
    """RESISTAI_ALLOW_NO_AUTH=true disables the auth gate (dev mode)."""
    server = _load_app(monkeypatch, RESISTAI_ALLOW_NO_AUTH="true")
    client, p = _client(server)
    try:
        # Auth is skipped, so body validation runs and rejects the empty body.
        assert client.post("/v1/predict/binding", json={}).status_code == 422
    finally:
        p.stop()
