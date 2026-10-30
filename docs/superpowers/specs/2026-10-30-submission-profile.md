# ResistAI submission profile

Authorized scope: user requested completing the hackathon work, including submission.
Build on upstream 3b9f4c8fd380bc1985b0276e7e1ac3a9b8e219f0. Keep legacy research pipeline out of the judge-facing application.

One workflow: authenticate, enter SMILES, calculate RDKit descriptors, explicitly opt into NVIDIA Nemotron through Nebius Token Factory, inspect unreviewed commentary and a machine-readable response record. No provider call on the descriptor-only path. Errors never substitute generated fixture data.

Use a small FastAPI interface, with all application/API routes authenticated and a minimal public liveness endpoint. Use text rendering and browser-side JSON export. No server file-serving or legacy API routes. Reject cross-origin state changes and oversized inputs. Persist conservative model-attempt quotas in SQLite, shared by workers, with no refunds for failures. Use a persistent mounted volume and a single deployed replica.

Publishing is gated on source distribution rights and an explicit repository license. Submission is gated on real provider evidence, tested HTTPS access, an actual working-demo video, and authenticated Devpost submission. Those facts must not be inferred from CI mocks.
