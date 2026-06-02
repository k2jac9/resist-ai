"""Webhook / notification system for ResistAI pipeline events.

Enables integration with external services (Slack, email, CI/CD)
when pipeline runs complete or other significant events occur.
"""
from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import logging
import os
import socket
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)

EVENTS = [
    "pipeline.started",
    "pipeline.completed",
    "pipeline.failed",
    "molecule.generated",
    "binder.designed",
    "experiment.completed",
]

# Allow plain-HTTP/private destinations only when explicitly opted in (local dev).
_ALLOW_PRIVATE_WEBHOOKS = os.environ.get(
    "RESISTAI_ALLOW_PRIVATE_WEBHOOKS", ""
).lower() in ("1", "true", "yes")


def _validate_webhook_url(url: str) -> None:
    """Reject webhook URLs that could enable SSRF.

    Enforces an https scheme and refuses hosts that resolve to private,
    loopback, link-local, or otherwise non-public IP ranges (e.g. cloud
    metadata endpoints). Set RESISTAI_ALLOW_PRIVATE_WEBHOOKS=true to relax
    this for local development.
    """
    parsed = urlparse(url)
    allowed_schemes = {"http", "https"} if _ALLOW_PRIVATE_WEBHOOKS else {"https"}
    if parsed.scheme not in allowed_schemes:
        raise ValueError(
            f"Webhook URL must use one of {sorted(allowed_schemes)} (got {parsed.scheme!r})"
        )
    host = parsed.hostname
    if not host:
        raise ValueError("Webhook URL has no host")
    if _ALLOW_PRIVATE_WEBHOOKS:
        return
    try:
        infos = socket.getaddrinfo(host, parsed.port or 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise ValueError(f"Webhook host does not resolve: {host}") from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
            raise ValueError(
                f"Webhook host {host} resolves to a non-public address ({ip}); refused"
            )


@dataclass
class WebhookConfig:
    url: str
    events: list[str] = field(default_factory=lambda: ["pipeline.completed"])
    headers: dict[str, str] = field(default_factory=dict)
    secret: str = ""
    active: bool = True


class WebhookManager:
    """Manages webhook registrations and dispatches events."""

    def __init__(self) -> None:
        self._hooks: list[WebhookConfig] = []
        self._history: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    # -- registration --------------------------------------------------------

    def register(
        self,
        url: str,
        events: list[str] | None = None,
        headers: dict[str, str] | None = None,
        secret: str = "",
    ) -> WebhookConfig:
        """Register a new webhook endpoint."""
        resolved_events = events or ["pipeline.completed"]
        invalid = [e for e in resolved_events if e not in EVENTS]
        if invalid:
            raise ValueError(f"Unknown event(s): {invalid}")
        _validate_webhook_url(url)
        hook = WebhookConfig(
            url=url,
            events=resolved_events,
            headers=headers or {},
            secret=secret,
        )
        with self._lock:
            self._hooks.append(hook)
        logger.info("Registered webhook %s for %s", url, resolved_events)
        return hook

    def unregister(self, url: str) -> bool:
        """Remove a webhook by URL. Returns True if found."""
        with self._lock:
            before = len(self._hooks)
            self._hooks = [h for h in self._hooks if h.url != url]
            removed = len(self._hooks) < before
        if removed:
            logger.info("Unregistered webhook %s", url)
        return removed

    # -- dispatch ------------------------------------------------------------

    def dispatch(self, event: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
        """Send *event* to every matching active webhook (blocking)."""
        if event not in EVENTS:
            raise ValueError(f"Unknown event: {event}")
        with self._lock:
            targets = [h for h in self._hooks if h.active and event in h.events]
        results: list[dict[str, Any]] = []
        for hook in targets:
            results.append(self._deliver(hook, event, payload))
        return results

    def dispatch_async(self, event: str, payload: dict[str, Any]) -> None:
        """Fire-and-forget dispatch in a background thread."""
        t = threading.Thread(
            target=self.dispatch, args=(event, payload), daemon=True
        )
        t.start()

    # -- delivery ------------------------------------------------------------

    def _deliver(
        self, hook: WebhookConfig, event: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        body = json.dumps(
            {"event": event, "timestamp": time.time(), "data": payload},
            default=str,
        )
        headers = {
            "Content-Type": "application/json",
            "X-ResistAI-Event": event,
            **hook.headers,
        }
        if hook.secret:
            headers["X-ResistAI-Signature"] = self._sign_payload(body, hook.secret)

        result: dict[str, Any] = {"url": hook.url, "event": event}
        start = time.monotonic()
        try:
            # Re-validate at delivery time to guard against DNS rebinding /
            # a hook constructed without going through register().
            _validate_webhook_url(hook.url)
            resp = requests.post(hook.url, data=body, headers=headers, timeout=10)
            result["status"] = resp.status_code
            result["ok"] = 200 <= resp.status_code < 300
        except (requests.RequestException, ValueError) as exc:
            result["status"] = 0
            result["ok"] = False
            result["error"] = str(exc)
            logger.warning("Webhook delivery failed for %s: %s", hook.url, exc)
        result["duration_ms"] = round((time.monotonic() - start) * 1000, 1)

        with self._lock:
            self._history.append(result)
            if len(self._history) > 500:
                self._history = self._history[-500:]
        return result

    @staticmethod
    def _sign_payload(payload: str, secret: str) -> str:
        """HMAC-SHA256 hex signature."""
        return hmac.new(
            secret.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()

    # -- introspection -------------------------------------------------------

    def get_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return recent delivery history (newest first)."""
        with self._lock:
            return list(reversed(self._history[-limit:]))

    def list_hooks(self) -> list[dict[str, Any]]:
        """Return serialisable list of registered webhooks."""
        with self._lock:
            return [
                {
                    "url": h.url,
                    "events": h.events,
                    "active": h.active,
                    "has_secret": bool(h.secret),
                }
                for h in self._hooks
            ]


# -- Slack helpers -----------------------------------------------------------

def slack_webhook(webhook_url: str) -> WebhookConfig:
    """Pre-configured :class:`WebhookConfig` for Slack incoming webhooks."""
    return WebhookConfig(
        url=webhook_url,
        events=["pipeline.completed", "pipeline.failed"],
        headers={"Content-Type": "application/json"},
    )


def format_slack_message(event: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Format a pipeline event as a Slack Block Kit message."""
    color = "#2eb886" if "completed" in event else "#dc3545"
    header = f"ResistAI | {event}"
    fields = [
        {"type": "mrkdwn", "text": f"*{k}:*\n{v}"}
        for k, v in list(payload.items())[:8]
    ]
    blocks: list[dict[str, Any]] = [
        {"type": "header", "text": {"type": "plain_text", "text": header}},
    ]
    if fields:
        blocks.append({"type": "section", "fields": fields})
    return {
        "attachments": [
            {
                "color": color,
                "blocks": blocks,
            }
        ]
    }
