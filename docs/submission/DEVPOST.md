# Devpost draft

**Title:** ResistAI: Evidence-First Research Copilot  
**Tagline:** Turn molecular calculations into inspectable research briefs, with Nemotron commentary kept separate from evidence.  
**Track:** Best Apps and Agents  
**Built with:** Python, RDKit, FastAPI, SQLite, Nebius Token Factory, NVIDIA Nemotron.

## Inspiration

Research prototypes can produce confident narratives faster than they produce reliable evidence. ResistAI asks a narrower question: can a researcher see exactly what was calculated, what a model said, and what is still unknown in one inspectable record?

## What it does

The Evidence Review workflow accepts a molecular SMILES structure and calculates six RDKit descriptors. The user can explicitly request an NVIDIA Nemotron explanation through Nebius Token Factory. Calculations and generated commentary are presented separately, and the downloadable JSON includes software version, canonical structure fingerprint, evidence ID, and observed provider-response metadata.

This is research software. It does not establish biological activity, clinical safety, treatment suitability, or regulatory eligibility.

## How we built it

A dedicated authenticated FastAPI application exposes the bounded evidence-review workflow. RDKit computes descriptors on the server. The model integration sends those descriptors to Nebius's OpenAI-compatible endpoint and requests a structured response referencing only evidence D1. The application validates response shape and citation IDs, preserves unreviewed status, and records requested and returned model identifiers, timing, hashes, and available usage metadata.

SQLite atomically reserves model attempts before inference. Its shared persistent budget survives process restarts and concurrent requests. Failure does not refund a reservation or substitute a simulated success. Authentication, explicit opt-in, bounded request bodies, and browser-side record export keep the demonstration small enough to inspect.

## Challenges and what we learned

The hardest boundary is between computation and interpretation. A well-formed model response is not a scientifically validated result. We designed the interface and record format to preserve that distinction, including when inference is unavailable.

Existing prototype features also needed careful separation. The judge-facing application excludes inherited orchestration, unverified candidate rankings, and unsupported biological or regulatory claims.

## What changed during the hackathon

ResistAI began as Team BioHack's earlier health/life-sciences prototype. This submission reuses that foundation. The October 30 work adds or strengthens the Nebius/Nemotron evidence-review path, honest failure handling, response metadata, descriptor provenance, a focused authenticated application, durable request admission, tests, and submission documentation. We do not claim the entire codebase was created during this event.

## Next steps

Evaluate explanation quality with domain experts, add independently curated evidence, and measure whether the interface helps users distinguish calculations from unsupported conclusions. Biological effectiveness would require appropriate experimental evidence beyond this software demonstration.

## Required release fields

Do not submit this draft until these are real and independently checked:

- Public licensed code URL: PENDING RIGHTS AND LICENSE.
- Working HTTPS demo URL: PENDING DEPLOYMENT AND ACCEPTANCE.
- Public YouTube URL, under three minutes: PENDING ACTUAL RECORDING.
- Private judge credentials: PENDING SECURE CONFIGURATION.
- Live Nebius receipt and actual model identifier: PENDING AUTHENTICATED CALL.
- Team list and accepted invitations: PENDING VERIFIED PARTICIPANTS.
- Final technology feedback: PENDING OBSERVED LIVE EXPERIENCE.

Submission representative must verify eligibility and any form attestations. Do not invent participant identity, consent, legal authority, or demographic information.
