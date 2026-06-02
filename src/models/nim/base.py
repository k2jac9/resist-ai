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
    """Load NVIDIA API key from env or .env file."""
    key = os.environ.get("NVIDIA_API_KEY", "")
    if not key:
        env_path = os.path.join(os.getcwd(), ".env")
        if os.path.exists(env_path):
            try:
                for line in open(env_path):
                    line = line.strip()
                    if line.startswith("NVIDIA_API_KEY="):
                        key = line.split("=", 1)[1].strip().strip('"').strip("'")
            except Exception:
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

    # Retry config for transient failures (429 / 5xx / timeouts).
    _MAX_RETRIES = 3
    _BACKOFF_BASE = 2.0

    def _post(self, endpoint: str, payload: dict, timeout: int | None = None) -> dict | str:
        """POST to a NIM endpoint with retry/backoff, return parsed JSON or raw text."""
        if not self._available:
            raise RuntimeError("NIM client not available (no API key)")

        url = ENDPOINTS[endpoint]
        req_timeout = timeout or self._timeout
        t0 = time.time()
        resp = None

        for attempt in range(self._MAX_RETRIES):
            try:
                resp = requests.post(
                    url, headers=self._headers(), json=payload, timeout=req_timeout,
                )
            except (requests.Timeout, requests.ConnectionError) as exc:
                if attempt == self._MAX_RETRIES - 1:
                    raise RuntimeError(f"NIM {endpoint} request failed: {exc}") from exc
                delay = self._BACKOFF_BASE ** attempt
                logger.warning("NIM %s network error (%s); retry in %.0fs", endpoint, exc, delay)
                time.sleep(delay)
                continue

            # Retry on rate-limit and server errors, honoring Retry-After.
            if resp.status_code == 429 or 500 <= resp.status_code < 600:
                if attempt == self._MAX_RETRIES - 1:
                    break
                retry_after = resp.headers.get("Retry-After")
                try:
                    delay = float(retry_after) if retry_after else self._BACKOFF_BASE ** attempt
                except ValueError:
                    delay = self._BACKOFF_BASE ** attempt
                logger.warning(
                    "NIM %s returned %d; retry %d/%d in %.0fs",
                    endpoint, resp.status_code, attempt + 1, self._MAX_RETRIES, delay,
                )
                time.sleep(delay)
                continue
            break

        elapsed = (time.time() - t0) * 1000

        if resp is None or resp.status_code != 200:
            code = resp.status_code if resp is not None else "no response"
            body = resp.text[:300] if resp is not None else ""
            raise RuntimeError(f"NIM {endpoint} returned {code}: {body}")

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
