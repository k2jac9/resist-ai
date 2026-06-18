"""Thread-safe lazy singletons for NIM and Nebius LLM clients.

Provides process-wide `get_nim()` / `get_llm()` accessors that initialize
on first use under a lock to prevent duplicate construction under concurrent
FastAPI / Gradio requests.
"""
from __future__ import annotations

import logging
import threading
from typing import Any, Optional

logger = logging.getLogger(__name__)

_nim: Optional[Any] = None
_llm: Optional[Any] = None
_nim_lock = threading.Lock()
_llm_lock = threading.Lock()


def get_nim() -> Optional[Any]:
    """Return shared NIMClient or None if construction failed."""
    global _nim
    if _nim is not None:
        return _nim
    with _nim_lock:
        if _nim is None:
            try:
                from ..models.nim_client import NIMClient
                _nim = NIMClient()
            except Exception as exc:
                logger.warning("NIMClient init failed: %s", exc, exc_info=True)
                _nim = None
    return _nim


def get_llm() -> Optional[Any]:
    """Return shared NebisLLM or None if construction failed."""
    global _llm
    if _llm is not None:
        return _llm
    with _llm_lock:
        if _llm is None:
            try:
                from ..models.llm_client import NebisLLM
                _llm = NebisLLM()
            except Exception as exc:
                logger.warning("NebisLLM init failed: %s", exc, exc_info=True)
                _llm = None
    return _llm


def reset_clients() -> None:
    """Reset cached clients (for tests)."""
    global _nim, _llm
    with _nim_lock:
        _nim = None
    with _llm_lock:
        _llm = None
