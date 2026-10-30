"""Launch policy for the Gradio UI's paid-provider operations."""
from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any


def launch_options(env: Mapping[str, str] | None = None) -> dict[str, Any]:
    settings = os.environ if env is None else env
    host = settings.get("RESISTAI_HOST", "127.0.0.1").strip()
    if not host or any(c.isspace() for c in host):
        raise ValueError("Invalid RESISTAI_HOST")
    try:
        port = int(settings.get("PORT", "7860"))
    except (TypeError, ValueError):
        raise ValueError("Invalid PORT") from None
    if not 1 <= port <= 65535:
        raise ValueError("Invalid PORT")
    username = settings.get("RESISTAI_UI_USER", "").strip()
    password = settings.get("RESISTAI_UI_PASSWORD", "")
    public = host not in {"127.0.0.1", "localhost", "::1"}
    if public and not (username and password):
        raise ValueError("Public binding requires UI authentication")
    if bool(username) != bool(password):
        raise ValueError("Both UI authentication settings are required")
    if password and (len(password) < 16 or password.lower().startswith(("your_", "your-"))):
        raise ValueError("UI authentication requires a non-placeholder password of at least 16 characters")
    return {"server_name": host, "server_port": port, "share": False,
            "show_error": False, "auth": (username, password) if password else None}
