"""Route-level submission profile tests; provider calls are controlled fixtures."""
import json

import pytest
from fastapi.testclient import TestClient

from src.submission_app import create_app


@pytest.fixture
def config(tmp_path):
    return {
        "RESISTAI_UI_USER": "judge",
        "RESISTAI_UI_PASSWORD": "correct-horse-battery-staple",
        "RESISTAI_QUOTA_DB": str(tmp_path / "quota.sqlite3"),
        "RESISTAI_MODEL_PER_MINUTE": "1",
        "RESISTAI_MODEL_PER_DAY": "2",
        "RESISTAI_MODEL_LIFETIME": "3",
        "NEBIUS_API_KEY": "unit-test-placeholder",
    }


@pytest.fixture
def client(config):
    with TestClient(create_app(config)) as result:
        yield result


def post(client, payload, **kwargs):
    return client.post("/api/review", auth=("judge", "correct-horse-battery-staple"),
                       headers={"X-ResistAI-Request": "review"}, json=payload, **kwargs)


def test_requires_auth_even_when_legacy_bypass_enabled(config):
    config["RESISTAI_ALLOW_NO_AUTH"] = "true"
    config.pop("RESISTAI_UI_PASSWORD")
    with pytest.raises(ValueError):
        create_app(config)


def test_rejects_weak_password_and_missing_key(config):
    config["RESISTAI_UI_PASSWORD"] = "short"
    with pytest.raises(ValueError):
        create_app(config)
    config["RESISTAI_UI_PASSWORD"] = "correct-horse-battery-staple"
    config.pop("NEBIUS_API_KEY")
    with pytest.raises(ValueError):
        create_app(config)


def test_health_is_minimal_and_application_requires_auth(client):
    assert client.get("/healthz").json() == {"status": "ok"}
    for path in ("/", "/api/review"):
        response = client.get(path) if path == "/" else client.post(path, json={})
        assert response.status_code == 401
    assert client.get("/", auth=("judge", "wrong")).status_code == 401
    assert client.get("/", auth=("judge", "correct-horse-battery-staple")).status_code == 200
    for path in ("/docs", "/openapi.json", "/file=/etc/passwd", "/gradio_api/file=/etc/passwd"):
        assert client.get(path).status_code == 404


def test_descriptor_only_never_invokes_model(client, monkeypatch):
    def forbidden():
        pytest.fail("descriptor-only request invoked model")

    monkeypatch.setattr("src.research_review._llm", forbidden)
    response = post(client, {"smiles": "CCO", "use_model": False})
    assert response.status_code == 200
    record = response.json()["record"]
    assert record["model_status"] == "not_requested"
    assert record["descriptor_evidence"]["canonical_smiles"] == "CCO"
    assert record["receipt"] is None


def test_rejects_cross_origin_and_missing_header(client):
    auth = ("judge", "correct-horse-battery-staple")
    assert client.post("/api/review", auth=auth, json={}).status_code == 403
    response = client.post("/api/review", auth=auth, json={"smiles": "CCO"},
                           headers={"X-ResistAI-Request": "review", "Origin": "https://attacker.test"})
    assert response.status_code == 403


@pytest.mark.parametrize("payload", [
    {"smiles": "not a molecule", "use_model": True},
    {"smiles": "CCO", "use_model": "false"},
    {"smiles": "CCO", "use_model": 1},
    {"smiles": "CCO", "unexpected": True},
    {"smiles": ""},
    {"smiles": "C" * 4097},
    [],
])
def test_invalid_inputs_do_not_reach_provider_or_spend_quota(client, monkeypatch, payload):
    def forbidden(*args, **kwargs):
        pytest.fail("invalid input reached model")

    monkeypatch.setattr("src.submission_app.review_descriptors", forbidden)
    assert post(client, payload).status_code == 422


def test_oversize_body_is_rejected(client):
    response = client.post("/api/review", auth=("judge", "correct-horse-battery-staple"),
                           headers={"X-ResistAI-Request": "review", "Content-Type": "application/json"},
                           content=json.dumps({"smiles": "C" * 9000}))
    assert response.status_code == 413


def test_admission_is_durable_and_failure_does_not_refund(config, monkeypatch):
    calls = []

    def unavailable(smiles, use_model=False):
        calls.append((smiles, use_model))
        raise RuntimeError("sensitive upstream detail")

    monkeypatch.setattr("src.submission_app.review_descriptors", unavailable)
    with TestClient(create_app(config)) as first:
        response = post(first, {"smiles": "CCO", "use_model": True})
        assert response.status_code == 503
        assert "sensitive" not in response.text
    with TestClient(create_app(config)) as restarted:
        assert post(restarted, {"smiles": "CCO", "use_model": True}).status_code == 429
    assert calls == [("CCO", True)]


def test_valid_result_preserves_provider_record_and_is_not_cached(client, monkeypatch):
    record = {"status": "recorded", "model_status": "response_received",
              "receipt": {"model": "nvidia/test", "request_id": "fixture-only"}}
    monkeypatch.setattr("src.submission_app.review_descriptors",
                        lambda *a, **kw: ("UNREVIEWED MODEL COMMENTARY", json.dumps(record)))
    response = post(client, {"smiles": "CCO", "use_model": True})
    assert response.json()["record"] == record
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
