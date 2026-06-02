# ResistAI — Audit & Remediation

A full audit of the codebase (security, correctness, dependencies, docs, tests)
was performed and the findings below were remediated in this branch.

## Critical / High

| # | Finding | Fix |
|---|---------|-----|
| 1 | Safety/ADMET scores were `random.uniform` numbers presented as model output (`pipeline/stages.py`). | `stage_safety_score` now uses the real RDKit-descriptor `ADMETPredictor` + Tanimoto `OffTargetAnalyzer`, keyed on SMILES, deterministic, with a `provenance` field. No structure → flagged unavailable, not fabricated. |
| 2 | Screening affinity fell back to `random.uniform(0.35,0.97)` (`pipeline/orchestrator.py`). | Replaced with a deterministic, structure-based `heuristic_binding_score`, explicitly tagged `heuristic_docking`. Druggability fallback no longer random. |
| 3 | README SDK example referenced nonexistent API (`MoleculeOptimizer` unexported, `pipeline.run()`, `results.candidates`, `composite_score`). | Exported `MoleculeOptimizer`/`Candidate`/`OptimizationResult` from `src.sdk`; rewrote the example to the real `Pipeline(...).fold().screen().dock().run()` and `MoleculeOptimizer(...).run()` API. |
| 4 | README CLI command `python -m src.pipeline.orchestrator --target ...` was a no-op. | Corrected to `python -m src.cli run --pathogen ... --max-drugs ... --novel`. |
| 5 | `RegulatoryReport` had a duplicate `from_dict`/`__str__` (pasted `PipelineResults` code) causing a latent `TypeError`. | Removed the misplaced methods; gave `PipelineResults` its own `from_dict`/`__str__`. |
| 6 | API auth failed **open** — empty `RESISTAI_API_KEY` disabled auth (`api/server.py`). | Fails **closed** (503) unless `RESISTAI_ALLOW_NO_AUTH=true`; timing-safe `hmac.compare_digest`. |
| 7 | CORS `allow_origins=["*"]` with `allow_credentials=True`. | Origins from `RESISTAI_CORS_ORIGINS` allowlist; credentials only when not wildcard; methods/headers narrowed. |
| 8 | SSRF — arbitrary webhook URLs posted unvalidated (`sdk/webhooks.py`). | `https`-only + DNS resolution blocking private/loopback/link-local/reserved IPs, at register and delivery. Opt-out: `RESISTAI_ALLOW_PRIVATE_WEBHOOKS`. |
| 9 | All FastAPI handlers were `async def` doing blocking I/O on the event loop. | Converted handlers to `def` so FastAPI runs them in a threadpool. |
| 10 | Dockerfile `python:3.13-slim` (rdkit/torch wheels unavailable) + ran as root. | Pinned `python:3.11-slim`; added a non-root `app` user. |

## Medium

- Path traversal / constrained SSRF in `pdb_fetcher.py` → strict PDB (`^[A-Z0-9]{4}$`) / UniProt (`^[A-Z0-9]{6,10}$`) validation.
- Internal exceptions leaked to API clients → generic `"Internal server error"`; details logged server-side only.
- Unpinned `>=` deps → upper-bounded ranges; pruned 5 unused deps (`py3Dmol`, `pubchempy`, `scikit-learn`, `biopython`, `aiofiles`); heavy `torch`/`transformers` moved to `requirements-ml.txt`.
- Unrelated Node `package.json`/`package-lock.json` (`agentic-flow`) removed; duplicate 5MB `ResistAI.png` removed.
- Config drift in `settings.yaml` (Nebius URL, branding, NIM vs Nebius models) corrected.
- NIM client retry was single-shot → retry with backoff + `Retry-After`, retries 5xx/timeouts.

## Low

- Insecure `tempfile.mktemp()` → `tempfile.mkstemp()` (`ui/__init__.py`).
- Stale duplicate `docs/README.md` → stub pointing at root README.
- `examples/quickstart.ipynb` referenced nonexistent `src.api.main` → `src.api`.
- Deprecated FastAPI `on_event("startup")` → lifespan handler.
- Added `requirements-dev.txt`; added auth tests (`tests/test_api_auth.py`); test suite runs (49 passing).

## New environment variables

| Variable | Purpose |
|----------|---------|
| `RESISTAI_API_KEY` | Enables the REST API; sent by clients as `X-API-Key`. |
| `RESISTAI_ALLOW_NO_AUTH` | `true` runs the API with no auth (local dev only). |
| `RESISTAI_CORS_ORIGINS` | Comma-separated CORS allowlist. |
| `RESISTAI_ALLOW_PRIVATE_WEBHOOKS` | `true` allows webhooks to non-public/HTTP URLs (dev only). |
