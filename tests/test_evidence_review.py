"""End-to-end descriptor review, with only the external HTTP exchange simulated."""
import json
import httpx
import pytest


def test_offline_review_does_not_construct_a_model(monkeypatch):
    from src import research_review as r
    def forbidden():
        pytest.fail("Offline review constructed model")
    monkeypatch.setattr(r, "_llm", forbidden)
    md, raw = r.review_descriptors("CCO", False)
    record = json.loads(raw)
    assert record["model_status"] == "not_requested"
    assert record["descriptor_evidence"]["values"]["molecular_weight"] == pytest.approx(46.069, abs=.02)
    assert record["receipt"] is None
    assert "unreviewed" not in md.lower()


def _review_client(monkeypatch, content):
    from src import research_review as r
    from src.models.llm_client import NebisLLM
    from src.models.nebius_transport import NebiusTransport
    def handler(req):
        body = json.loads(req.content)
        assert body["response_format"] == {"type": "json_object"}
        assert "46.069" in body["messages"][-1]["content"]
        return httpx.Response(200, json={"id":"response-test", "model":"nvidia/nemotron-3-super-120b-a12b", "choices":[{"finish_reason":"stop", "message":{"content":json.dumps(content)}}]})
    model = NebisLLM(transport=NebiusTransport(api_key="test-key", client=httpx.Client(transport=httpx.MockTransport(handler))))
    monkeypatch.setattr(r, "_llm", lambda: model)


def test_live_review_uses_computed_evidence_and_preserves_receipt(monkeypatch):
    from src.research_review import review_descriptors
    _review_client(monkeypatch, {"summary":"Computed descriptors alone do not establish efficacy.","limitations":["No assay measurements."],"evidence_ids":["D1"]})
    md, raw = review_descriptors("CCO", True)
    record = json.loads(raw)
    assert record["model_status"] == "response_received"
    assert record["receipt"]["model"].startswith("nvidia/")
    assert record["receipt"]["request_id"] == "response-test"
    assert record["clinical_validation"] is False
    assert "UNREVIEWED MODEL COMMENTARY" in md
    assert "test-key" not in raw


@pytest.mark.parametrize("content", [
    {"summary":"text","limitations":["unknown"],"evidence_ids":["invented-paper"]},
    {"summary":"text","limitations":[],"evidence_ids":["D1"]},
    {"summary":"text","limitations":["unknown"],"evidence_ids":["D1"],"clinical_validation":True},
    {"summary":42,"limitations":["unknown"],"evidence_ids":["D1"]},
])
def test_invalid_model_review_is_not_promoted(monkeypatch, content):
    from src.research_review import review_descriptors
    _review_client(monkeypatch, content)
    md, raw = review_descriptors("CCO", True)
    record = json.loads(raw)
    assert record["model_status"] == "rejected"
    assert record["model_commentary"] is None
    assert record["error"] == "invalid_review_schema"
    assert record["receipt"]["request_id"] == "response-test"
    assert "UNREVIEWED MODEL COMMENTARY" not in md


def test_missing_key_is_explicit_and_retains_only_calculations(monkeypatch):
    from src.research_review import review_descriptors
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)
    md, raw = review_descriptors("CCO", True)
    record = json.loads(raw)
    assert record["model_status"] == "unavailable"
    assert record["error"] == "missing_api_key"
    assert record["receipt"] is None
    assert record["model_commentary"] is None


def test_invalid_structure_never_calls_llm(monkeypatch):
    from src import research_review as r
    def forbidden():
        pytest.fail("Invalid structure reached model")
    monkeypatch.setattr(r, "_llm", forbidden)
    _, raw = r.review_descriptors("NOT_A_MOLECULE", True)
    assert json.loads(raw)["status"] == "failed"


def test_model_text_is_rendered_as_untrusted_text(monkeypatch):
    from src.research_review import review_descriptors
    _review_client(monkeypatch, {"summary":"<script>alert(1)</script>", "limitations":["<img src=x onerror=evil()>"], "evidence_ids":["D1"]})
    md, raw = review_descriptors("CCO", True)
    assert "<script>" not in md and "<img" not in md
    assert "&lt;script&gt;" in md
