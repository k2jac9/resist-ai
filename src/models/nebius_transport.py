"""Bounded Nebius chat transport. Configuration is not evidence of inference."""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlsplit

import httpx

DEFAULT_BASE_URL = "https://api.tokenfactory.us-central1.nebius.com/v1"
DEFAULT_MODEL = "nvidia/nemotron-3-super-120b-a12b"
_ALLOWED_HOSTS = frozenset({"api.tokenfactory.us-central1.nebius.com", "api.tokenfactory.nebius.com", "api.studio.nebius.com"})
_MODEL_RE = re.compile(r"[A-Za-z0-9_.\-/]{1,200}\Z")


class InferenceError(RuntimeError):
    """A redacted, machine-readable failure; never includes provider response bodies."""


@dataclass(frozen=True)
class CompletionEvidence:
    text: str
    model: str
    requested_model: str
    request_id: str
    endpoint: str
    elapsed_ms: float
    usage: dict[str, int]
    input_sha256: str
    output_sha256: str
    received_at: str
    status: str = "response_received"

    def to_dict(self) -> dict[str, Any]:
        """Return receipt metadata without prompt, response text, or credentials."""
        result = asdict(self)
        result.pop("text")
        return result


def _base_url(value: str) -> str:
    try:
        p = urlsplit(value)
        valid = (p.scheme == "https" and p.hostname in _ALLOWED_HOSTS
                 and p.port in (None, 443) and not p.username and not p.password
                 and p.path.rstrip("/") == "/v1" and not p.query and not p.fragment)
    except (ValueError, TypeError):
        valid = False
    if not valid:
        raise InferenceError("invalid_base_url")
    return value.rstrip("/")


class NebiusTransport:
    """One non-retried call with per-operation HTTP timeouts; the caller owns any injected HTTP client.

    Receipts are thread-local because existing UI/pipeline clients may be shared.
    They describe an observed response, not clinical validity or independent attestation.
    """

    def __init__(self, model: str | None = None, *, api_key: str | None = None,
                 base_url: str | None = None, timeout: float = 45.0,
                 client: httpx.Client | None = None) -> None:
        self.model = model or os.environ.get("NEBIUS_MODEL") or DEFAULT_MODEL
        if not isinstance(self.model, str) or not _MODEL_RE.fullmatch(self.model):
            raise InferenceError("invalid_model")
        self.base_url = _base_url(base_url or os.environ.get("NEBIUS_BASE_URL") or DEFAULT_BASE_URL)
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or not 1 <= timeout <= 120:
            raise InferenceError("invalid_timeout")
        self.timeout = float(timeout)
        key = os.environ.get("NEBIUS_API_KEY", "") if api_key is None else api_key
        if not isinstance(key, str) or any(c in key for c in "\r\n"):
            raise InferenceError("invalid_api_key")
        key = key.strip()
        self._key = "" if key.lower().startswith(("your_", "your-", "replace_", "replace-")) else key
        self._client = client
        self._state = threading.local()

    @property
    def configured(self) -> bool:
        return bool(self._key)

    @property
    def last_result(self) -> CompletionEvidence | None:
        return getattr(self._state, "last_result", None)

    def complete_result(self, prompt: str, system: str = "", max_tokens: int = 2048,
                        temperature: float = 0.3, json_mode: bool = False) -> CompletionEvidence:
        self._state.last_result = None
        if not self.configured:
            raise InferenceError("missing_api_key")
        if type(max_tokens) is not int or not 1 <= max_tokens <= 4096:
            raise InferenceError("invalid_max_tokens")
        if not isinstance(prompt, str) or not prompt.strip() or not isinstance(system, str) or len(prompt) + len(system) > 64000:
            raise InferenceError("invalid_prompt")
        if isinstance(temperature, bool) or not isinstance(temperature, (int, float)) or not math.isfinite(temperature) or not 0 <= temperature <= 2:
            raise InferenceError("invalid_temperature")
        if type(json_mode) is not bool:
            raise InferenceError("invalid_json_mode")
        messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
        body: dict[str, Any] = {"model": self.model, "messages": messages,
                                "max_tokens": max_tokens, "temperature": temperature}
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        start = time.monotonic()
        owned = self._client is None
        client = self._client if self._client is not None else httpx.Client()
        try:
            with client.stream("POST", self.base_url + "/chat/completions", json=body,
                               headers={"Authorization": f"Bearer {self._key}"},
                               timeout=self.timeout, follow_redirects=False) as response:
                if response.status_code != 200:
                    raise InferenceError(f"provider_http_{response.status_code}")
                raw_body = bytearray()
                for chunk in response.iter_bytes():
                    if len(raw_body) + len(chunk) > 262144:
                        raise InferenceError("response_too_large")
                    raw_body.extend(chunk)
            try:
                data = json.loads(raw_body)
                choice = data["choices"][0]
                content = choice["message"]["content"]
                finish = choice["finish_reason"]
                model = data["model"]
            except (ValueError, KeyError, IndexError, TypeError):
                raise InferenceError("invalid_provider_response") from None
            if finish != "stop":
                raise InferenceError("incomplete_provider_response")
            if not isinstance(content, str) or not content.strip() or len(content) > 65536:
                raise InferenceError("invalid_provider_content")
            if not isinstance(model, str) or not _MODEL_RE.fullmatch(model):
                raise InferenceError("invalid_provider_model")
            if json_mode:
                try:
                    obj = json.loads(content, parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
                    if not isinstance(obj, dict):
                        raise ValueError()
                except ValueError:
                    raise InferenceError("invalid_json") from None
            usage_raw = data.get("usage") or {}
            usage = {k: v for k, v in usage_raw.items() if k in {"prompt_tokens", "completion_tokens", "total_tokens"}
                     and type(v) is int and v >= 0} if isinstance(usage_raw, dict) else {}
            request_id = data.get("id") or response.headers.get("x-request-id", "")
            if not isinstance(request_id, str) or len(request_id) > 200:
                request_id = ""
            evidence = CompletionEvidence(
                text=content, model=model, requested_model=self.model,
                request_id=request_id, endpoint=self.base_url,
                elapsed_ms=round((time.monotonic() - start) * 1000, 3), usage=usage,
                input_sha256=hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
                output_sha256=hashlib.sha256(content.encode()).hexdigest(),
                received_at=datetime.now(timezone.utc).isoformat(),
            )
            self._state.last_result = evidence
            return evidence
        except httpx.TimeoutException:
            raise InferenceError("provider_timeout") from None
        except httpx.RequestError:
            raise InferenceError("provider_network_error") from None
        finally:
            if owned:
                client.close()
