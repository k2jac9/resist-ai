"""Small authenticated judge-facing app; no legacy pipeline or server file exports."""
from __future__ import annotations

import json
import os
import secrets
import threading
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette.concurrency import run_in_threadpool

from src.request_limits import QuotaExceeded, RequestLimits
from src.research_integrity import descriptor_evidence
from src.research_review import review_descriptors


def create_app(config=None) -> FastAPI:
    config = os.environ if config is None else config
    username = config.get("RESISTAI_UI_USER", "").strip()
    password = config.get("RESISTAI_UI_PASSWORD", "")
    if not username or len(password) < 16 or password.lower() in {
        "change-me-before-deploy", "your-password-here", "correct-horse-battery-staple-placeholder"
    }:
        raise ValueError("Submission profile requires a username and a strong password of at least 16 characters")
    if not config.get("NEBIUS_API_KEY", "").strip():
        raise ValueError("Submission profile requires NEBIUS_API_KEY")
    limits = RequestLimits(
        config.get("RESISTAI_QUOTA_DB", ""),
        int(config.get("RESISTAI_MODEL_PER_MINUTE", "4")),
        int(config.get("RESISTAI_MODEL_PER_DAY", "40")),
        int(config.get("RESISTAI_MODEL_LIFETIME", "200")),
    )
    slots = threading.BoundedSemaphore(2)
    app = FastAPI(title="ResistAI Evidence Review", docs_url=None, redoc_url=None, openapi_url=None)
    security = HTTPBasic()

    def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
        user_ok = secrets.compare_digest(credentials.username.encode(), username.encode())
        password_ok = secrets.compare_digest(credentials.password.encode(), password.encode())
        if not (user_ok & password_ok):
            raise HTTPException(401, "Authentication required", headers={"WWW-Authenticate": "Basic"})
        return credentials.username

    @app.middleware("http")
    async def response_headers(request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        return response

    @app.get("/healthz")
    def health():
        # Liveness only: this deliberately does not claim provider connectivity.
        return {"status": "ok"}

    @app.get("/", dependencies=[Depends(authenticate)])
    def index():
        nonce = secrets.token_urlsafe(24)
        page = Path(__file__).with_name("submission.html").read_text(encoding="utf-8")
        return HTMLResponse(page.replace("__NONCE__", nonce), headers={
            "Content-Security-Policy": "default-src 'none'; script-src 'nonce-" + nonce
            + "'; style-src 'nonce-" + nonce
            + "'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
        })

    def execute(smiles, use_model):
        if not slots.acquire(blocking=False):
            raise HTTPException(503, "Review service busy; retry later")
        try:
            try:
                descriptor_evidence(smiles)
            except (ValueError, ImportError):
                raise HTTPException(422, "Structure could not be calculated") from None
            if use_model:
                try:
                    limits.reserve()
                except QuotaExceeded:
                    raise HTTPException(429, "Model attempt limit reached; descriptors remain available") from None
                except Exception:
                    raise HTTPException(503, "Model admission unavailable") from None
            try:
                summary, raw = review_descriptors(smiles, use_model=use_model)
                return {"summary": summary, "record": json.loads(raw)}
            except Exception:
                raise HTTPException(503, "Review unavailable; no replacement model result was produced") from None
        finally:
            slots.release()

    @app.post("/api/review", dependencies=[Depends(authenticate)])
    async def review(request: Request):
        origin = request.headers.get("origin")
        if request.headers.get("x-resistai-request") != "review":
            raise HTTPException(403, "Same-origin review header required")
        if origin:
            parsed = urlsplit(origin)
            if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() != request.headers.get("host", "").lower():
                raise HTTPException(403, "Cross-origin request rejected")
        if request.headers.get("content-type", "").split(";")[0].strip().lower() != "application/json":
            raise HTTPException(415, "JSON required")
        body = bytearray()
        async for chunk in request.stream():
            if len(body) + len(chunk) > 8192:
                raise HTTPException(413, "Request too large")
            body.extend(chunk)
        try:
            value = json.loads(body)
        except (ValueError, UnicodeDecodeError):
            raise HTTPException(422, "Invalid JSON") from None
        if (not isinstance(value, dict) or set(value) - {"smiles", "use_model"}
                or not isinstance(value.get("smiles"), str)
                or not value["smiles"].strip() or len(value["smiles"]) > 4096
                or type(value.get("use_model", False)) is not bool):
            raise HTTPException(422, "Supply SMILES and a boolean model opt-in")
        return await run_in_threadpool(execute, value["smiles"], value.get("use_model", False))

    return app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(create_app(), host=os.getenv("RESISTAI_UI_HOST", "127.0.0.1"),
                port=int(os.getenv("PORT", os.getenv("RESISTAI_UI_PORT", "7860"))),
                access_log=False)
