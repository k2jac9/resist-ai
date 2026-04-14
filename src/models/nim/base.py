"""Shared HTTP logic for NVIDIA NIM Biology API."""
from __future__ import annotations

import logging
import os
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)

NIM_BASE = "https://health.api.nvidia.com/v1/biology"

ENDPOINTS = {
    "esmfold": f"{NIM_BASE}/nvidia/esmfold",
    "evo2": f"{NIM_BASE}/arc/evo2-40b/generate",
    "boltz2": f"{NIM_BASE}/mit/boltz2/predict",
    "molmim": f"{NIM_BASE}/nvidia/molmim/generate",
    "rfdiffusion": f"{NIM_BASE}/ipd/rfdiffusion/generate",
    "proteinmpnn": f"{NIM_BASE}/ipd/proteinmpnn/predict",
    "diffdock": f"{NIM_BASE}/mit/diffdock",
}


def _get_api_key() -> str:
    """Load NVIDIA API key from env (or .env via python-dotenv if not yet loaded)."""
    key = os.environ.get("NVIDIA_API_KEY", "")
    if not key:
        try:
            from dotenv import load_dotenv
            load_dotenv(override=False)
            key = os.environ.get("NVIDIA_API_KEY", "")
        except ImportError:
            pass
    return key


class NIMBase:
    """Base class with shared HTTP logic for NIM endpoints."""

    def __init__(self, api_key: str | None = None, timeout: int = 120) -> None:
        self._api_key = api_key or _get_api_key()
        self._timeout = timeout
        self._available = bool(self._api_key)
        if not self._available:
            logger.warning("NVIDIA_API_KEY not set; NIM client unavailable")
        else:
            logger.info("NIM client initialized (7 biology endpoints)")

    @property
    def available(self) -> bool:
        return self._available

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def _post(self, endpoint: str, payload: dict, timeout: int | None = None) -> dict | str:
        """POST to a NIM endpoint, return parsed JSON or raw text."""
        if not self._available:
            raise RuntimeError("NIM client not available (no API key)")

        url = ENDPOINTS[endpoint]
        t0 = time.time()
        resp = requests.post(
            url, headers=self._headers(), json=payload,
            timeout=timeout or self._timeout,
        )
        elapsed = (time.time() - t0) * 1000

        if resp.status_code == 429:
            logger.warning("NIM rate limited on %s; retrying after 3s", endpoint)
            time.sleep(3)
            resp = requests.post(
                url, headers=self._headers(), json=payload,
                timeout=timeout or self._timeout,
            )
            elapsed = (time.time() - t0) * 1000

        if resp.status_code != 200:
            raise RuntimeError(
                f"NIM {endpoint} returned {resp.status_code}: {resp.text[:300]}"
            )

        content_type = resp.headers.get("content-type", "")
        if "application/json" in content_type:
            data = resp.json()
            if isinstance(data, dict):
                data["_elapsed_ms"] = elapsed
            return data
        return resp.text

    def health_check(self) -> dict[str, bool]:
        """Quick check which NIM endpoints are reachable."""
        results = {}
        for name in ENDPOINTS:
            try:
                resp = requests.post(
                    ENDPOINTS[name], headers=self._headers(),
                    json={}, timeout=5,
                )
                results[name] = resp.status_code in (200, 400, 422)
            except Exception:
                results[name] = False
        return results
