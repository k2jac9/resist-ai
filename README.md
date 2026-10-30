# ResistAI

Research evidence tooling for antimicrobial-resistance research.

**Research prototype, not a validated drug-discovery or clinical system.** This branch repairs evidence presentation and adds a bounded NVIDIA Nemotron review path through Nebius Token Factory. It does not establish biological activity, patient safety, regulatory eligibility, or a completed hackathon submission.

## Start with the Evidence Review tab

Supply a molecular SMILES string. ResistAI computes actual RDKit molecular descriptors, records the canonical input fingerprint and software version, and optionally requests Nemotron commentary about the evidence and its limitations. The default `CCO` is a software test input, not a proposed AMR treatment.

Offline calculation makes no provider request. Model review requires explicit opt-in and server-side credentials. A successful response records requested and returned model IDs, response ID when provided, endpoint, elapsed time, reported token usage, and input/output hashes. These are application observations, not independently signed attestations. Generated commentary remains unreviewed, even after its JSON shape and allowed evidence ID pass validation.

The Co-folding Response tab displays returned Boltz-2 structural confidence metrics without converting them into binding affinity or clinical probabilities. The Descriptors tab calculates properties rather than fabricating a safety score. Legacy orchestration remains accessible, but its output is prominently marked **unverified**. Explicit simulations stay labeled simulated; UI execution failures do not silently turn into fixture results.

## Setup

The existing CI and Docker runtime use Python 3.11. Keep the repository's pinned requirements; the local execution note documents a different available test environment and does not replace full CI qualification.

```bash
git clone https://github.com/k2jac9/resist-ai.git
cd resist-ai
git checkout fix/nebius-evidence-integrity-20261030
python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
cp .env.example .env
python -m pytest -q
python -m src.app
```

The repository currently requires access. No open-source license or public-release authorization is conferred by this change. Without provider keys, the descriptor workflow works locally and provider-backed operations report unavailable.

### Nebius configuration

Set these in the process environment or root `.env`, never in source control or a browser bundle:

```dotenv
NEBIUS_API_KEY=
NEBIUS_BASE_URL=https://api.tokenfactory.us-central1.nebius.com/v1
NEBIUS_MODEL=nvidia/nemotron-3-super-120b-a12b
```

The endpoint/model pair follows the [Nebius Nemotron cookbook](https://github.com/nebius/token-factory-cookbook/blob/main/models/nemotron/nemotron3-super-120B.md). Actual account availability and successful inference must be verified separately. Changing `NEBIUS_MODEL` does not establish hackathon eligibility; check the returned model and relevant model license.

Run the same bounded review path from the command line:

```bash
python scripts/smoke_nebius.py --smiles CCO --output /tmp/resistai-nebius-smoke.json
```

Exit 0 means a response passed the review-format checks. Exit 2 means the model review did not complete successfully. Missing keys, HTTP errors, timeouts, malformed/truncated responses and rejected review schemas remain explicit. No live provider success was established in the implementation environment.

`NVIDIA_API_KEY` separately enables NVIDIA-hosted biology API requests. Hosting on NVIDIA infrastructure alone is not proof of using an NVIDIA-authored open model. Local descriptor computation is not an NVIDIA model call.

### Access and spend controls

The UI defaults to loopback, disables public sharing, and hides raw error messages. To bind to a public interface, configure `RESISTAI_HOST=0.0.0.0` plus `RESISTAI_UI_USER` and `RESISTAI_UI_PASSWORD` with a non-placeholder password of at least 16 characters. Put the service behind HTTPS. In Docker, explicitly set the bind host and credentials in the environment; otherwise the loopback default is not reachable through a published container port.

The Gradio queue bounds concurrent provider work and queued requests. The Nebius transport bounds prompt/output sizes and per-call token requests, uses per-operation HTTP timeouts, and does not retry or follow redirects. These are **not** account-wide spending limits, durable quotas, tenant isolation, or a total wall-clock deadline. Add deployment-level authentication, rate limits, budget limits and cancellation before untrusted public operation. REST API authentication remains separately configured with `RESISTAI_API_KEY`.

## Architecture and retained interfaces

- `src/models/nebius_transport.py`: bounded HTTP exchange and thread-local response receipts.
- `src/models/llm_client.py`: historical `NebisLLM` compatibility interface with research-only prompts.
- `src/research_review.py`: descriptor evidence plus optional, schema-checked model commentary.
- `src/research_integrity.py`: descriptor calculations, output classification and report rendering.
- `src/research_execution.py`: shared legacy UI/export path with no silent UI fixture substitution.
- `src/ui/`: research-first Gradio interface and compatible callback signatures.
- `src/ui_security.py`: loopback/default and public-bind authentication policy.
- `src/models/nim/boltz2.py`: reject malformed responses and distinguish observed values from defaults.

Existing SDK, CLI, FastAPI, generation and orchestration modules remain in the repository. They have not all been migrated to the new evidence contract. In particular, the legacy orchestrator still uses unverified hardcoded target/compound records, heuristic fallbacks and model-use metadata that must not be treated as validated provenance. Legacy regulatory, explainability, cost-comparison and presentation scripts are not qualified for public claims and are no longer presented as default UI features.

## Verification and release gates

See [the implementation and readiness record](docs/NEBIUS_READINESS_2026-10-30.md), [design](docs/superpowers/specs/2026-10-30-evidence-integrity-design.md), and [plan](docs/superpowers/plans/2026-10-30-evidence-integrity.md).

Tests exercise real descriptor calculations and application boundaries; provider responses are simulated at the HTTP boundary. They do not establish successful live API calls, biological correctness, scientific benchmark quality, or deployment readiness. A full repository CI run under the pinned dependencies, a live model receipt, authenticated hosted acceptance, license/ownership approval, public judge access and a truthful sub-three-minute video remain release gates.

## Provenance and ownership

ResistAI originated with Team BioHack at the Evolved 25 health/life-sciences hackathon. This work reuses that repository and explicitly separates inherited functionality from the October 30 evidence-integrity changes. Earlier README results and performance/regulatory claims were not independently established by this execution and are not repeated as verified results.

[Selectra](https://github.com/k2jac9/selectra) is a separate private sibling project. This change does not alter its scope or licensing.

Copyright (c) 2026 Team BioHack. All rights reserved. License terms to be determined.
