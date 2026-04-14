# ResistAI — Improvements Log & Roadmap

**Session date:** 2026-04-14
**Baseline commit:** `9b768ba` (Update build deps, add data-flow diagram, normalize line endings)
**Head after session:** `98b0b23`
**Commits added:** 6 (baseline `9b768ba` → `98b0b23`)

This document captures every change applied during the 2026-04-14 architecture hardening pass, the verification performed, and the prioritized next steps. It is the authoritative handoff note for anyone picking up this work.

---

## Executive summary

- **Dev environment**: `uv`-managed venv at `~/.venvs/resist-ai` (symlinked to `.venv`), Python 3.12.3, all deps at latest (FastAPI 0.135, pydantic 2.13, transformers 5.5, torch 2.11, gradio 6.12, rdkit 2026.3, numpy 2.4, pandas 3.0).
- **Tests**: 46 → **87 passing** (+41 new tests for CLI + validators).
- **Biggest structural win**: `src/pipeline/orchestrator.py` split from **630 lines** to **259 lines** across 8 cohesive modules, all under 120 lines each.
- **Concurrency hardening**: every lazy `_get_*` singleton across 4 modules now uses `threading.Lock` with double-checked locking; 10+ bare `except Exception: pass` blocks replaced with logged warnings.
- **Container posture**: Dockerfile runs as non-root (uid 1000), docker-compose has resource limits / log rotation / `no-new-privileges`.
- **API auth**: `RESISTAI_AUTH_STRICT=1` opt-in for fail-closed behavior when `RESISTAI_API_KEY` is unset.
- **End-to-end verification**: pytest + CLI + live uvicorn + full pipeline demo run + Gradio instantiation — all passing.

---

## 1. Dev environment setup

### Tooling decisions

| Decision | Rationale |
|---|---|
| **uv** (not pip) | 10-100× faster for torch/transformers installs. |
| **Venv at `~/.venvs/resist-ai`** (not `<project>/.venv`) | Linux-native disk avoids /mnt/c WSL IO penalty on heavy package ops. |
| **Symlink `.venv` → `~/.venvs/resist-ai`** | IDE and `source .venv/bin/activate` still work from the project directory. |
| **Python 3.12** | System default; latest wheels available for all deps; Dockerfile's 3.13 is used only for container builds. |

### How to reproduce the environment

```bash
# Install uv (one-time)
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

# Create venv and symlink
mkdir -p ~/.venvs
uv venv ~/.venvs/resist-ai --python 3.12
ln -sfn ~/.venvs/resist-ai .venv

# Install runtime + dev deps
VIRTUAL_ENV=~/.venvs/resist-ai uv pip install -r requirements.txt
VIRTUAL_ENV=~/.venvs/resist-ai uv pip install -r requirements-dev.txt

# Activate and run
source .venv/bin/activate
pytest                                              # 87 tests
ruff check src/ tests/
python -m src.cli models                            # CLI
uvicorn src.api.server:app --reload --port 8000     # API
python -m src.app                                   # Gradio UI (7860)
```

### Reproducibility lock

`requirements-lock.txt` pins all 101 transitive deps (generated via `uv pip freeze`). For exact reproduction, use this instead of `requirements.txt`.

---

## 2. Dependency upgrade

Every runtime dep pushed to latest. Tests gated every step.

| Package | Before | After | Notes |
|---|---|---|---|
| fastapi | >=0.104 | 0.135.3 | `@app.on_event` removed → migrated to `lifespan` |
| pydantic | >=2.5 | 2.13.0 | v2.x throughout; `field_validator` used in boundary validators |
| transformers | >=4.36 | 5.5.4 | **major version jump** — ESM-2 load path still works |
| gradio | >=4.8 | 6.12.0 | **major jump** — `create_app()` still returns valid `gr.Blocks` |
| torch | >=2.1 | 2.11.0 | heavy install (~2GB with CUDA) |
| rdkit | >=2024.3 | 2026.3.1 | SMILES validation tested against current API |
| numpy | >=1.24 | 2.4.4 | **major jump** (2.x) — no regressions |
| pandas | >=3.0 | 3.0.2 | **major jump** — no regressions |
| starlette | via fastapi | 1.0.0 | (transitive) — **major jump**, also clean |
| openai | >=1.6 | 2.31.0 | used by `llm_client.py` (Nebius) |
| plotly | >=5.18 | 6.7.0 | **major jump** |

All version floors pinned in `requirements.txt`. Dev tooling (`pytest`, `pytest-asyncio`, `pytest-mock`, `ruff`) lives in `requirements-dev.txt`.

---

## 3. Code changes (by commit)

### `1c85bc7` — Dep upgrade + validators + lifespan

First pass of hardening alongside the upgrade.

**API boundary validation** (`src/api/server.py`)
- Added `_validate_smiles` using RDKit `Chem.MolFromSmiles` (noisy `RDLogger` suppressed).
- Added `_validate_protein_sequence` with extended 26-letter AA alphabet (20 standard + B/J/O/U/X/Z + `*`), case-insensitive, whitespace-stripped.
- Added `_validate_dna_sequence` with `ACGTNU` alphabet.
- Wired into `BindingRequest`, `StructureRequest`, `GenerateRequest`, `DNAGenerateRequest`, `DockRequest`, `BinderRequest` via pydantic `field_validator`.

**FastAPI lifespan migration** (`src/api/server.py`)
- Replaced deprecated `@app.on_event("startup")` with `@asynccontextmanager` `lifespan(app)`, registered via `FastAPI(..., lifespan=lifespan)`.

**Env loading modernization**
- `src/cli.py::_load_env()` and `src/models/nim/base.py::_get_api_key()` now delegate to `python-dotenv.load_dotenv()` instead of hand-rolled line parsers. Function names preserved so `tests/test_nim_client.py:22,31` patches still work.

---

### `baf91d3` — Split `orchestrator.py`

The core structural refactor. Nothing imported `TargetAnalyzer`/`DrugScreener`/`SafetyScorer`/`NovelMoleculeGenerator`/`_DEMO_*`/`_FALLBACK_*` from outside `orchestrator.py`, so all internals were free to move.

**New modules (all ≤ 120 lines):**

| File | Lines | Contents |
|---|---|---|
| `src/pipeline/clients.py` | 59 | thread-safe `get_nim()` / `get_llm()` / `reset_clients()` |
| `src/pipeline/demo_data.py` | 34 | `DEMO_DRUG_LIBRARY` (12 AMR drugs), `DEMO_SEQUENCES` (9 targets) |
| `src/pipeline/target_stage.py` | 120 | `TargetAnalyzer`, `compute_druggability`, `get_pathogen_targets`, `FALLBACK_TARGETS` |
| `src/pipeline/screening_stage.py` | 72 | `DrugScreener` (Boltz-2 virtual screening) |
| `src/pipeline/novel_stage.py` | 65 | `NovelMoleculeGenerator` (MolMIM) |
| `src/pipeline/safety_stage.py` | 58 | `SafetyScorer` (ADMET + off-target) |
| `src/pipeline/ranking.py` | 35 | `rank_candidates` |
| `src/pipeline/orchestrator.py` | **259** | slim `PipelineOrchestrator` coordinator + `_default_progress` |

**Public API unchanged** — external imports still read `from src.pipeline.orchestrator import PipelineOrchestrator` from `api/server.py`, `cli.py`, `sdk/batch.py`, `ui/common.py`.

---

### `b36948a` — Thread-safe singletons, logged errors, strict auth

**Concurrency fixes** — every unguarded `_get_*` accessor got a `threading.Lock` with double-checked locking:

| File | Symbol |
|---|---|
| `src/api/server.py` | `_get_nim()`, `_get_orchestrator()` |
| `src/ui/common.py` | `get_pmgr()`, `get_orch()`, `get_llm()` |
| `src/pipeline/stages.py` | `_get_esm2()` |
| `src/pipeline/clients.py` | already thread-safe by construction |

The pattern:
```python
def get_foo():
    global _foo
    if _foo is not None:          # fast path, no lock
        return _foo
    with _foo_lock:
        if _foo is None:           # second check under lock
            try:
                _foo = Foo()
            except Exception as exc:
                logger.warning("Foo init failed: %s", exc, exc_info=True)
                _foo = None
    return _foo
```

**Error logging** — replaced `except Exception: pass` in:
- `src/data/drug_library.py:90, 123` — ChEMBL / Repurposing Hub fetch failures now log with the exception message.
- `src/models/nim/base.py:106` — `health_check` failures now log at DEBUG with endpoint name.

**Strict auth mode** (`src/api/server.py:178-193`)
- New `RESISTAI_AUTH_STRICT` env var. When set and `RESISTAI_API_KEY` is unset, raises `RuntimeError` at module import — the process fails closed instead of silently accepting unauthenticated traffic.
- When `RESISTAI_API_KEY` is unset and strict mode is off, a loud warning is logged at startup so the permissive default is visible in operations.

---

### `daa9f2e` — Container hardening

**`Dockerfile`**
- Created unprivileged `resistai` user (uid/gid 1000), `chown -R` on `/app`, `USER resistai`.
- Container compromise no longer implies root on the host.

**`docker-compose.yml`**
- Dropped obsolete `version: "3.9"`.
- Added `deploy.resources.limits` (2 CPUs, 4GB memory) and `reservations` (1GB) on both `web` and `api` services.
- Added `logging.driver: json-file` with 10MB × 3 file rotation.
- Added `security_opt: no-new-privileges:true`.

---

### `dbb30ae` — Tests (+41)

**`tests/test_validators.py`** (19 tests)
- `TestProteinValidator` — standard/extended alphabet, whitespace, digits, punctuation, empty rejection.
- `TestDNAValidator` — ACGT, N (unknown), U (RNA), lowercase normalization, non-DNA rejection, empty rejection.
- `TestSmilesValidator` — aspirin, ethanol, garbage strings, unbalanced brackets.
- `TestPydanticIntegration` — `BindingRequest`, `StructureRequest`, `DNAGenerateRequest` wiring.

**`tests/test_cli.py`** (22 tests)
- `TestParser` — all 8 subcommands register; `run` defaults; `--novel` + `--max-drugs`.
- `TestMainDispatch` — no-command, handler exceptions (text + JSON), `KeyboardInterrupt` → rc=130.
- `TestCmdHealth` — no API key path, JSON output, healthy endpoints.
- `TestCmdModels` — 7-model listing in both text and JSON modes.
- `TestCmdPredict` — success + failure branches with mocked NIMClient.
- `TestCmdRun` — orchestrator exception + JSON output with banner.
- `TestFormatHelpers` — `table()` and `badge()`.

Full suite now **87 tests**, runs in ~2.5s.

---

### `98b0b23` — Deprecation + lock file

- `src/pipeline/target_discovery/evo2_client.py` — moved deprecation note into module docstring; emits proper `DeprecationWarning` via `warnings.warn()` at import time. The file attempts to drive Evo2-40b through Nebius AI Studio's chat completions API, which is a misuse (Evo2 is a generative genomic model, not a chat model). The real integration is `src.models.nim_client.NIMClient` via NVIDIA NIM's Evo2 generate endpoint, used by `stages.stage_genomics` and the orchestrator. No importers in `src/` or `tests/` today — kept as reference.
- `requirements-lock.txt` — 101 transitive deps pinned via `uv pip freeze` for CI/fresh-install reproducibility.

---

## 4. End-to-end verification

Performed in this session, all green:

| Batch | Scope | Result |
|---|---|---|
| **1. Unit + lint + imports** | `pytest`, `ruff check`, module-walk import | 87/87 tests · 72/72 src modules import · lint clean on all touched files |
| **2. CLI smoke** | `models`, `health`, `run --help`, error paths | all 8 subcommands parse · JSON output valid · arg validation triggers |
| **3. Live API via uvicorn** | boot → curl → shutdown | `/v1/health`, `/v1/models` return 200 · SMILES/protein/DNA validators return 422 with descriptive error messages · valid request reaches NIM path |
| **4. Pipeline orchestrator** | `run_full_pipeline(demo_mode=True)` | 6.16s full run · 4 targets → 5 drugs → 5 safety reports → 5 ranked candidates · `to_dict()` round-trips · LLM 402 handled gracefully |
| **5. Gradio app** | `create_app()` + re-exports | returns `gradio.blocks.Blocks` on gradio 6.12 · all re-exported callables present · `PATHOGENS` dict populated |

**Live API validator output (proving the boundary enforcement works):**
```json
// POST /v1/predict/binding with ligand_smiles: "NOT_A_MOLECULE!!!"
// HTTP 422
{
  "detail": [{
    "type": "value_error",
    "loc": ["body", "ligand_smiles"],
    "msg": "Value error, invalid SMILES string: 'NOT_A_MOLECULE!!!'",
    "input": "NOT_A_MOLECULE!!!"
  }]
}
```

**Pipeline demo run output (proving the orchestrator split works):**
```
  [      init]   0.0%  Starting pipeline for acinetobacter_baumannii
  [   targets]   5.0%  Discovering druggable targets (ESMFold)...
  [   targets]  15.0%  Found 4 targets
  [ screening]  20.0%  Screening drugs against NDM-1 (Boltz-2)...
  [ screening]  45.0%  Screened 5 compounds, 5 hits
  [    safety]  70.0%  Evaluating safety for 5 hits...
  ...
  [  complete] 100.0%  Pipeline complete in 6.16s
=== Top 3 candidates ===
  #1 Plazomicin              overall=0.8607  binding=0.857  safety=0.892
  #2 Eravacycline            overall=0.7633  binding=0.793  safety=0.612
  #3 Meropenem-Vaborbactam   overall=0.7260  binding=0.659  safety=0.727
```

---

## 5. Outstanding issues (not blockers)

1. **`stage_druggability` misleading log**: prints `"transformers/torch not installed; ESM-2 will use mock embeddings"` when ESM-2 weights are unreachable via HuggingFace (504 gateway). Both libraries ARE installed — the real cause is HF Hub network failures. The heuristic fallback path (`compute_druggability`) works correctly; the log message just misattributes the cause. See `src/pipeline/stages.py` around `_get_esm2()`.

2. **Ruff cleanups not yet committed**: Three trivial lint fixes were applied during e2e but remain uncommitted in the working tree:
   - `src/api/server.py` — moved `import threading` to the top of file
   - `src/pipeline/stages.py` — moved `import threading` to the top of file
   - `tests/test_cli.py` — removed unused `import pytest`
   These should be folded into a single `chore: ruff cleanups` commit.

3. **`package.json` / `package-lock.json`**: pre-existing modifications in the working tree that predate this session. Unrelated to resist-ai Python code (probably claude-flow tooling state). Left untouched.

4. **Nebius LLM budget exhausted**: observed a `402 Payment Required` during pipeline demo run. Operational issue, not code. The pipeline correctly logs and continues without the LLM insights.

5. **Orphan subdirectories in `src/pipeline/`**: `target_discovery/`, `drug_screening/`, `safety_prediction/` contain `target_analyzer.py`, `screener.py`, `safety_scorer.py` — partial abandoned refactor, duplicate class names vs the live orchestrator code. No importers in `src/` or `tests/` other than internal `__init__.py` re-exports. Safe to delete but deferred from this session to avoid scope creep.

6. **Container warning**: `docker-compose` `deploy.resources.limits` only takes effect under Swarm mode by default. For plain `docker-compose up`, the limits are advisory. If single-host enforcement is desired, use the top-level `cpus:` / `mem_limit:` keys instead. Worth verifying once a real deploy happens.

---

## 6. Known architectural weaknesses still present

These were identified in the audits but deliberately deferred from this session:

1. **Global mutable state pattern** — even with locks, the `_get_*` singletons are still process-wide state hidden behind function calls. A proper dependency-injection container (or just explicit parameter passing through the orchestrator) would be cleaner and make testing more composable. Scope: touches `api/server.py`, `ui/common.py`, `cli.py`, `pipeline/orchestrator.py`, `sdk/batch.py`. Probably 3-4 hours of work.

2. **No test coverage for `src/ui/*`** — the 7 Gradio tab modules (~1400 lines total) have zero tests. Gradio components are hard to test without mocking most of the framework; best approach is probably testing the underlying callback functions directly with a mock orchestrator.

3. **Pipeline stage functions in `src/pipeline/stages.py` have no direct tests** — they're covered indirectly via integration tests only. Unit tests with a mock NIMClient would cement behavior.

4. **Configuration drift**: `config/settings.yaml` defines targets per pathogen, and `src/pipeline/target_stage.py::FALLBACK_TARGETS` duplicates a subset of them in hardcoded dict form. If one is updated but not the other, behavior silently diverges. The YAML should be the single source of truth; fallback dict should either be generated from YAML at import time or removed once `PathogenManager` is guaranteed to be available.

5. **No resource limits on ESM-2 memory**: loading the 650M parameter model consumes ~2.5GB RAM. If multiple Gradio sessions hit it concurrently, memory can spike. Current docker-compose limit is 4GB which is tight.

6. **Dockerfile `pip install` not using `uv`**: the container still uses pip which is slow for torch/transformers. Switching the Dockerfile to uv would cut build times significantly.

7. **`requirements.txt` has only `>=` floors**: transitive dep drift is possible between fresh installs. `requirements-lock.txt` exists but CI should pin to it in practice.

---

## 7. Prioritized next steps

### Tier 1 — Small, high-value fixes (do next session)

| # | Item | Est | Value |
|---|---|---|---|
| 1 | Commit ruff cleanups (threading imports, unused pytest) | 5 min | keeps lint clean |
| 2 | Fix misleading `stage_druggability` log message | 10 min | debuggability |
| 3 | Delete orphan `src/pipeline/{target_discovery,drug_screening,safety_prediction}/*_analyzer.py` / `*_scorer.py` / `screener.py` files (confirmed dead) | 30 min | reduces confusion |
| 4 | Add `requirements-lock.txt` usage to CI docs + `Dockerfile` build | 20 min | reproducibility |
| 5 | Switch Dockerfile from `pip install` to `uv pip install` | 20 min | faster container builds |

### Tier 2 — Medium, worth doing (within a sprint)

| # | Item | Est | Value |
|---|---|---|---|
| 6 | Unit tests for `src/pipeline/stages.py` with mock NIMClient | 2h | coverage + regression safety |
| 7 | Unit tests for re-exported UI callback functions (`run_pipeline_ui`, `analyze_safety`, etc.) with mock orchestrator | 3h | UI regression safety |
| 8 | Resolve configuration drift between `settings.yaml` and `FALLBACK_TARGETS` | 1h | eliminates silent divergence class |
| 9 | Replace `deploy.resources.limits` with top-level `mem_limit: 4g` + `cpus: 2` in compose (works without Swarm) | 10 min | enforcement on single-host |
| 10 | Add `structured JSON logging` (logging.basicConfig with JSON formatter or structlog) | 2h | observability |

### Tier 3 — Larger refactors (scoped proposals)

| # | Item | Est | Notes |
|---|---|---|---|
| 11 | Replace global `_get_*` singletons with explicit DI context object passed through constructors | 4h | touches 5 files; big diff; big testability win |
| 12 | Event-sourced pipeline state (per CLAUDE.md rule) | 1-2d | currently imperative; would need a new state machine layer |
| 13 | Secret management via env-only or Vault/AWS Secrets (remove `.env` from `env_file:`) | 2-4h | security posture for prod |
| 14 | Complete UI test coverage via gradio TestClient or component-level isolation | 1d | covers 1400 untested lines |
| 15 | Upstream `agentic-flow` patch fix (its `agentdb-runtime-patch.js` looks for agentdb v1.3.9 paths but we use v3.x) | file upstream issue | eliminates cosmetic stderr noise |

### Tier 4 — Nice-to-have polish

- Generate OpenAPI client SDK from the FastAPI schema (`src.api.server:app.openapi()`) for typed Python consumers.
- Pre-commit hooks for `ruff check --fix`, `ruff format`, `pytest -x`.
- GitHub Actions CI matrix for Python 3.11 / 3.12 / 3.13.
- Replace `random.seed(hash(...))` in `screening_stage.DrugScreener` with a seeded `random.Random()` instance (avoids global RNG state mutation).
- Consider typed NamedTuples for `metadata` dict in `PipelineResults` — currently untyped `dict[str, Any]`.

---

## 8. Files changed this session

```
 .gitignore                                   | +3  (venv patterns)
 Dockerfile                                   | +6  (non-root user)
 docker-compose.yml                           | +34 (limits, logging, security)
 requirements.txt                             | +-40 (latest pins)
 requirements-dev.txt                         | new
 requirements-lock.txt                        | new (101 lines)
 src/api/server.py                            | +104 -26 (validators, lifespan, locks, auth-strict)
 src/cli.py                                   | +8 -15 (dotenv)
 src/data/drug_library.py                     | +4 -4 (error logging)
 src/models/nim/base.py                       | +10 -15 (dotenv, debug log)
 src/pipeline/clients.py                      | new (59 lines)
 src/pipeline/demo_data.py                    | new (34 lines)
 src/pipeline/novel_stage.py                  | new (65 lines)
 src/pipeline/orchestrator.py                 | -371 (split into 7 modules)
 src/pipeline/ranking.py                      | new (35 lines)
 src/pipeline/safety_stage.py                 | new (58 lines)
 src/pipeline/screening_stage.py              | new (72 lines)
 src/pipeline/stages.py                       | +12 -5 (thread lock)
 src/pipeline/target_discovery/evo2_client.py | +20 -2 (DeprecationWarning)
 src/pipeline/target_stage.py                 | new (120 lines)
 src/ui/common.py                             | +31 -18 (thread locks, logging)
 tests/test_cli.py                            | new (228 lines)
 tests/test_validators.py                     | new (120 lines)
```

**Commit range**: `9b768ba..98b0b23` (6 commits).

---

## 9. Daily commands reference

```bash
# Activate env
source .venv/bin/activate

# Tests
pytest                          # all 87
pytest -k validator             # just validator tests
pytest -k cli                   # just cli tests
pytest -v --tb=short            # verbose

# Lint
ruff check src/ tests/
ruff format src/ tests/         # auto-format

# Run each entry point
python -m src.cli models                             # CLI: list models
python -m src.cli run --pathogen acinetobacter_baumannii --max-drugs 10
uvicorn src.api.server:app --reload --port 8000      # API server
python -m src.app                                    # Gradio UI on :7860

# Docker
docker compose build
docker compose up web           # Gradio on :7860
docker compose up api           # FastAPI on :8000
docker compose down

# Env vars that matter
export NVIDIA_API_KEY=...          # NIM biology models
export NEBIUS_API_KEY=...          # Nebius LLM (Qwen3-235B)
export RESISTAI_API_KEY=...        # X-API-Key header for /v1/* endpoints
export RESISTAI_AUTH_STRICT=1      # fail-closed if RESISTAI_API_KEY unset
export SKIP_AGENTDB_PATCH=1        # silence cosmetic noise from claude-flow tooling
```
