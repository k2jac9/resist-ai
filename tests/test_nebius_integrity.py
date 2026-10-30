"""Provider-boundary tests. Network I/O alone is replaced by httpx.MockTransport."""
import json
import httpx
import pytest


def provider(monkeypatch, handler, **kwargs):
    from src.models.nebius_transport import NebiusTransport
    monkeypatch.setenv("NEBIUS_API_KEY", "test-private-key")
    monkeypatch.delenv("NEBIUS_BASE_URL", raising=False)
    monkeypatch.delenv("NEBIUS_MODEL", raising=False)
    return NebiusTransport(client=httpx.Client(transport=httpx.MockTransport(handler)), **kwargs)


def response(content="Observed descriptors require separate biological validation.", **overrides):
    body = {"id": "chatcmpl-test", "model": "nvidia/nemotron-3-super-120b-a12b",
            "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": content}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 12, "total_tokens": 22}}
    body.update(overrides)
    return httpx.Response(200, json=body)


def test_configured_does_not_establish_live_inference(monkeypatch):
    p = provider(monkeypatch, lambda req: response())
    assert p.configured is True
    assert p.last_result is None


def test_missing_key_stops_before_network(monkeypatch):
    from src.models.nebius_transport import NebiusTransport, InferenceError
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)
    def forbidden(req):
        pytest.fail("Missing key reached network")
    p = NebiusTransport(api_key="", client=httpx.Client(transport=httpx.MockTransport(forbidden)))
    with pytest.raises(InferenceError, match="missing_api_key"):
        p.complete_result("test")
    assert p.last_result is None


def test_valid_call_records_provider_receipt_not_credentials(monkeypatch):
    def handler(req):
        body = json.loads(req.content)
        assert req.url.host == "api.tokenfactory.us-central1.nebius.com"
        assert req.url.path == "/v1/chat/completions"
        assert body["model"] == "nvidia/nemotron-3-super-120b-a12b"
        assert body["max_tokens"] == 512
        assert req.headers["authorization"] == "Bearer test-private-key"
        return response()
    p = provider(monkeypatch, handler)
    r = p.complete_result("research observations", max_tokens=512)
    assert r.status == "response_received"
    assert r.model == "nvidia/nemotron-3-super-120b-a12b"
    assert r.request_id == "chatcmpl-test"
    assert r.usage["total_tokens"] == 22
    assert r.elapsed_ms >= 0
    assert len(r.output_sha256) == 64
    assert "test-private-key" not in json.dumps(r.to_dict())
    assert "research observations" not in json.dumps(r.to_dict())


@pytest.mark.parametrize("bad", ["http://api.tokenfactory.nebius.com/v1", "https://evil.example/v1", "https://api.tokenfactory.nebius.com.evil.example/v1", "https://user:password@api.tokenfactory.nebius.com/v1", "https://api.tokenfactory.nebius.com/v1?key=secret", "https://api.tokenfactory.nebius.com:444/v1"])
def test_refuses_credential_destination_confusion(monkeypatch, bad):
    from src.models.nebius_transport import InferenceError
    with pytest.raises(InferenceError, match="invalid_base_url"):
        provider(monkeypatch, lambda req: response(), base_url=bad)


@pytest.mark.parametrize("status", [301, 302, 307, 308, 400, 401, 403, 429, 500, 503])
def test_http_failure_never_produces_success_or_leaks_body(monkeypatch, status):
    from src.models.nebius_transport import InferenceError
    p = provider(monkeypatch, lambda req: httpx.Response(status, text="test-private-key", headers={"Location": "https://evil.example"}))
    with pytest.raises(InferenceError) as exc:
        p.complete_result("test")
    assert "test-private-key" not in str(exc.value)
    assert p.last_result is None


@pytest.mark.parametrize("content", ["", "  ", None, 123])
def test_empty_or_nontext_output_is_not_success(monkeypatch, content):
    from src.models.nebius_transport import InferenceError
    p = provider(monkeypatch, lambda req: response(content))
    with pytest.raises(InferenceError):
        p.complete_result("test")
    assert p.last_result is None


@pytest.mark.parametrize("reason", ["length", "content_filter", "tool_calls", None])
def test_unfinished_output_is_not_success(monkeypatch, reason):
    from src.models.nebius_transport import InferenceError
    p = provider(monkeypatch, lambda req: response(choices=[{"finish_reason": reason, "message": {"content": "partial"}}]))
    with pytest.raises(InferenceError):
        p.complete_result("test")
    assert p.last_result is None


def test_json_mode_rejects_malformed_output(monkeypatch):
    from src.models.nebius_transport import InferenceError
    p = provider(monkeypatch, lambda req: response("not json"))
    with pytest.raises(InferenceError, match="invalid_json"):
        p.complete_result("test", json_mode=True)
    assert p.last_result is None


def test_success_is_cleared_by_later_failure(monkeypatch):
    from src.models.nebius_transport import InferenceError
    replies = iter([response(), httpx.Response(503)])
    p = provider(monkeypatch, lambda req: next(replies))
    p.complete_result("test")
    with pytest.raises(InferenceError):
        p.complete_result("test")
    assert p.last_result is None


@pytest.mark.parametrize("tokens", [0, -1, 4097, True, 1.5])
def test_invalid_token_budget_rejected_before_network(monkeypatch, tokens):
    from src.models.nebius_transport import InferenceError
    def forbidden(req):
        pytest.fail("Invalid budget reached provider")
    p = provider(monkeypatch, forbidden)
    with pytest.raises(InferenceError, match="invalid_max_tokens"):
        p.complete_result("test", max_tokens=tokens)


def test_timeout_is_redacted(monkeypatch):
    from src.models.nebius_transport import InferenceError
    def timeout(req):
        raise httpx.ReadTimeout("test-private-key", request=req)
    p = provider(monkeypatch, timeout)
    with pytest.raises(InferenceError, match="provider_timeout") as exc:
        p.complete_result("test")
    assert "test-private-key" not in str(exc.value)


def test_oversized_stream_stops_before_reading_the_entire_body(monkeypatch):
    from src.models.nebius_transport import InferenceError
    class ExcessiveBody(httpx.SyncByteStream):
        def __iter__(self):
            yield b"x" * 200000
            yield b"x" * 100000
            raise AssertionError("Client continued consuming an oversized body")
    p = provider(monkeypatch, lambda req: httpx.Response(200, stream=ExcessiveBody()))
    with pytest.raises(InferenceError, match="response_too_large"):
        p.complete_result("test")
    assert p.last_result is None
