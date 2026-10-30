# ResistAI evidence-integrity remediation

Baseline: k2jac9/resist-ai, 95dc342b1420c6287c7e4f0544b7c4a002cab583.
The user requested inspection, a plan, and execution, then explicitly requested a retry.

## Intent
Make the existing research prototype honest about computed descriptors, provider responses,
simulation, and missing evidence. Preserve the Python/Gradio architecture and private main.
This tranche is research software, not a clinically validated discovery platform.

## Approaches and decision
A full scientific pipeline rebuild has too many unqualified data/model dependencies for a
bounded remediation. A cosmetic relabel alone leaves fabricated outputs executable.
Selected by the implementer: repair the provider boundary and affected presentation/export
paths; retain the legacy orchestrator but mark its aggregate outputs unverified until its
input identities, affinity semantics, and per-stage provenance are qualified separately.

## Scope and limits
- Nebius Token Factory, configurable NVIDIA Nemotron model, bounded synchronous calls.
- Missing keys, provider failures, malformed/truncated replies must never become successes.
- Binding UI: actual provider result or explicit unavailable; never generate random scores.
- Safety UI: computed molecular descriptors only, never random ADMET or a safety PASS.
- Pipeline/report: explicit simulations; real legacy executions exported as unverified,
  not relabeled live because keys exist. Execution errors do not fall back to fixtures.
- Keep legacy callable signatures and app compatibility exports.
- Do not publish the repository, choose a license, merge, provision hosting, or claim live
  model qualification without evidence. Preserve Team BioHack attribution.
- No new sequence generation, protein design, or medicinal-chemistry optimization.
- No clinical, efficacy, regulatory eligibility, timeline, or cost-saving promises.

## Acceptance
Focused regression tests cover actual RDKit descriptors, invalid inputs, HTTP transport,
credential isolation, response validation, missing keys, truthful JSON export and errors.
Full upstream CI and authenticated provider/host acceptance remain distinct gates.
