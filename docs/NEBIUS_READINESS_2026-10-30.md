# ResistAI implementation and readiness record

Date: October 30, 2026. Baseline: `95dc342b1420c6287c7e4f0544b7c4a002cab583`.
Review branch: `fix/nebius-evidence-integrity-20261030`.

## Decision and scope

Retain Python, Gradio, FastAPI and existing provider interfaces. Repair the evidence boundary before expanding biological functionality. The new bounded demonstration is SMILES -> real descriptors -> optional Nemotron evidence review through Token Factory -> inspectable response receipt. It is a research-software demonstration, not drug validation.

The implementation is intentionally a review candidate. Main, repository visibility, Team BioHack ownership and license status remain unchanged. No hosting resources were provisioned and no submission or video upload was performed.

## Findings and executed changes

| Finding in the inspected baseline | Change in this branch | Remaining boundary |
|---|---|---|
| Safety UI used random numbers and implied live evidence from key presence | Actual RDKit descriptors; no invented ADMET, off-target or clinical verdict | Descriptors do not validate safety or drug identity |
| Binding UI fabricated fallback scores and conflated structure confidence with binding | Explicit errors and provider-native structural metrics | No assay or affinity calibration established |
| Empty Boltz responses were accepted as successful | Required observed confidence; finite/range validation; observed-fields tracking | Core legacy screening still needs its own metric/provenance migration |
| Report tab always used demo rows even in live mode | One execution/export path; actual returned record or explicit failure | Legacy records retain unverified scientific data and scores |
| Pipeline UI silently simulated after errors | Failure clears result tables; simulation requires explicit selection | Internal legacy fallbacks remain unqualified and visibly unverified |
| Nebius model/endpoint hardcoded to older models | Configurable allowlisted Token Factory transport; Nemotron default | Account model access and real inference still need verification |
| Model success inferred from configuration | Separate configured state, response receipt, error and rejected-schema states | Receipts are not signed attestations or proof of scientific validity |
| Public Gradio bind exposed provider operations | Loopback default; public bind requires explicit UI authentication | Durable quotas, rate controls and multi-user isolation still pending |
| Default presentation made unverified approval/clinical claims | Research-first UI and rewritten README; legacy regulatory views removed from default navigation | Legacy scripts/modules are retained, not scientifically rehabilitated |

## Verification actually executed

A sparse source overlay was built from the inspected repository files because a full authenticated checkout was not available in the execution container. Unchanged original modules were not all present locally. Empty package initializers used only by this local harness are excluded from publication.

- `GRADIO_ANALYTICS_ENABLED=False python -m pytest -q`: **116 passed** across the six newly added focused test modules. This is not the full original repository suite.
- `python -m compileall -q src scripts tests`: passed on the local overlay.
- Real RDKit descriptor calculations: tested canonical-equivalent input stability, invalid structures, limits and expected software-fixture values.
- HTTP-level provider tests: simulated only the external HTTP exchange, exercising the real transport, facade and review pipeline. Covered redirect refusal, secret redaction, status errors, timeouts, malformed/truncated responses, streamed-body size cap, missing keys, strict JSON and stale receipt behavior.
- Gradio app mounted through `gr.mount_gradio_app`: root and `/config` returned HTTP 200; 45 components were constructed. The actual Evidence Review callback computed `CCO` molecular weight 46.069 with no model requested. Opting into the model without a key returned `unavailable` / `missing_api_key` with no provider receipt.
- `python scripts/smoke_nebius.py --smiles CCO`: exit **2**, `missing_api_key`. Neither provider credential was configured. No live inference success is claimed.
- Self-review found and fixed malformed legacy collection handling with five observed failing regressions before the final passing run.

Local environment: Python 3.13.5, pytest 9.0.2, RDKit 2025.09.4, Gradio 6.5.1, pandas 2.2.3, Plotly 6.5.2 and httpx 0.28.1. These differ from the repository's Python 3.11/pinned dependencies. Requirements were not weakened to fit the local environment. Ruff was unavailable locally. Full repository lint/tests and dependency compatibility must be established by CI or a complete checkout.

The first manual UI harness bypassed Gradio's mount/launch initialization and failed with a missing config. Using the normal mount lifecycle fixed that harness. A subsequent harness assertion used the wrong JSON key and was corrected to the actual `descriptor_evidence.values` contract. No production workaround was added for either harness error.

No independent reviewer, browser-pixel acceptance, full entry-point import, Docker build, full SDK/API acceptance, hosted persistence, or live biology-model request was performed in this environment. The draft PR is the integration review gate, not a declaration of completion.

## Finish in this order

1. Run full CI with the existing Python 3.11 pins and inspect every failure. Do not merge based only on the focused overlay tests.
2. Configure `NEBIUS_API_KEY` in a trusted local environment or deployment secret manager. Run `scripts/smoke_nebius.py`, retain the returned requested/actual model identifiers and usage, and inspect the generated commentary. Never paste the credential into a submission or commit.
3. Qualify the narrow demo end to end with known, independently sourced input structures. Keep the legacy pipeline out of the central demo until its target/compound identity and per-stage provenance are repaired. Do not call structural confidence affinity, inhibition or efficacy.
4. Establish authenticated HTTPS judge access with bounded provider spend, cancellation, operational monitoring and a tested restart. A shared Gradio password and queue alone are not the complete public operating model.
5. Obtain Team BioHack ownership/attribution and licensing approval before publishing the repository. Add the chosen license only with that authority. Explain significant new work and pre-existing foundations in the submission.
6. Record the actual hosted behavior in a public video under three minutes, add concrete feedback from real Nebius/NVIDIA usage, verify teammate acceptance and confirm the submission receipt.

## Demonstration outline, not a completed recording

0:00-0:20: Show the research problem and state the prototype's limits.
0:20-0:55: Enter an independently sourced structure, calculate descriptors and inspect its fingerprint.
0:55-1:40: Explicitly request Nemotron review on Nebius; show returned model/receipt and commentary separated from calculations.
1:40-2:10: Show an invalid input or controlled provider failure without fabricated fallback data.
2:10-2:35: Inspect the JSON evidence record and explain what remains scientifically unverified.
2:35-2:45: Identify the reused foundation, new work, repository and hosted access.

Do not use simulated HTTP tests or offline fixture footage as evidence of live provider inference.

## Longer-term scientific and engineering work

Replace hardcoded target and compound records with independently verified identifiers, structures, dates and source fingerprints. Unify UI/API/SDK/CLI onto a typed per-stage record with explicit computed, predicted, simulated, unavailable and reviewed states. Preserve successful zero-valued metrics without heuristic replacement. Separate affinity outputs from structural confidence and evaluate against appropriate experimental reference data. Add proper data provenance, measured benchmark protocols and uncertainty handling before any scientific performance claim. Retire fabricated regulatory/explainability and cost-savings templates rather than treating deterministic output as validation.

Ruling: the bounded Evidence Review path and launch-policy guard were added to the original repair plan because they provide a testable sponsor-integration seam without representing the unqualified legacy pipeline as validated science. This does not substitute for the remaining scientific or hosted release gates.
