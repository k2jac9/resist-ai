# ResistAI Evidence Integrity Implementation Plan

> For agentic workers: use superpowers:executing-plans task by task.

**Goal:** Remove fabricated UI results and make Nebius inference and exports inspectable.
**Architecture:** A bounded HTTP client plus pure integrity/rendering functions; existing
Gradio callbacks retain their signatures and delegate to these boundaries.
**Tech Stack:** Python, httpx, RDKit, pytest, existing Gradio.
**Spec:** ../specs/2026-10-30-evidence-integrity-design.md

## Global Constraints
No default-branch changes, visibility/license changes, secret disclosure or fabricated results.
No claims that software tests validate biology or prove hosted inference.

## Review Focus
Provider redirects must not forward keys. Empty/truncated replies must not count as success.
Invalid SMILES must produce no descriptors. A failed live request must never yield fixtures.
Legacy metadata must not be promoted to verified provenance by a display flag.

## Task 1: Provider boundary
Create src/models/nebius_transport.py; update src/models/llm_client.py.
Tests: tests/test_nebius_integrity.py using httpx.MockTransport at the HTTP boundary.
- [x] Write/run failing tests: configured is not live, missing-key abstention, bounded requests,
  untrusted endpoint refusal, HTTP errors/redaction, truncated/invalid replies, valid receipt.
- [x] Implement the transport and preserve NebisLLM's public compatibility methods.
- [x] Run the targeted tests and syntax checks.

## Task 2: Evidence presentation
Create src/research_integrity.py; update UI safety, models, pipeline and report modules.
Tests: tests/test_research_integrity.py and tests/test_ui_integrity.py.
- [x] Write/run failing tests for canonical descriptors, invalid input and truthful modes.
- [x] Replace randomized safety/binding outputs, fail closed on provider errors, export actual
  legacy results as unverified; separate explicit simulations from provider-backed requests.
- [x] Run targeted tests and adapter integration tests.

## Task 3: Release preparation
Update README; create docs/NEBIUS_READINESS_2026-10-30.md and scripts/smoke_nebius.py.
- [x] Document audit, new versus inherited behavior, setup, release gates and demo outline.
- [x] Run all available local tests; record dependency/runtime and sparse-checkout limitations.
- [x] Publish to isolated review branch and open a draft PR; inspect source and CI afterward.

## Execution note

The provider/evidence tasks were exercised in a sparse local overlay, not a full original checkout. See the readiness record for exact commands, runtime differences and unexecuted gates. Full CI and live inference remain release requirements. The default UI includes a bounded descriptor-review callback and a public-bind authentication guard; these are deliberate additions, not pre-existing functionality.

## Publication verification

Draft PR #15 is open. Implementation head `be224c063a7421e468d846003c14ffae52ae3868` passed full GitHub CI: 342 tests, Python syntax checks and Ruff lint. The local-overlay limitation above still describes local execution; CI independently exercised the complete repository with its Python 3.11 dependencies. See [the publication verification record](../../VERIFICATION_2026-10-30.md). Live inference, independent review, deployment and publication/license gates remain open.
