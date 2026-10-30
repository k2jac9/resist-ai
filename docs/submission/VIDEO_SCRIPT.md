# Demonstration filming plan: target 2 minutes 40 seconds

Record the real hosted application after successful live acceptance. Use a clean browser; log in before filming. Hide account settings, keys, passwords, and unrelated tabs. Keep the UI legible. Captions should match the final spoken words. Do not replace a live model response with a fixture or imply that an edited wait was instantaneous.

| Time | Actual screen action | Narration |
| --- | --- | --- |
| 0:00–0:18 | Show application title and research boundary. | “ResistAI helps a researcher distinguish what a molecular calculation shows from what a language model says. This is research software, with no clinical validation.” |
| 0:18–0:48 | Leave opt-in off; run CCO; show descriptor values and fingerprint. | “Starting with a SMILES structure, RDKit calculates six descriptors. This record includes the canonical structure, software version, and an input fingerprint. No model request has been made.” |
| 0:48–1:25 | Enable model opt-in; run actual model call. Show wait honestly. | “Now I explicitly request an explanation from NVIDIA Nemotron through Nebius Token Factory. The model receives the calculated evidence and instructions to state its limits, without treatment advice or invented experiments.” |
| 1:25–1:58 | Show the returned unreviewed commentary and JSON receipt. | “The commentary remains unreviewed. The record shows the endpoint, requested and returned model, and response metadata. These are observations of the API exchange, not scientific validation.” |
| 1:58–2:15 | Download the actual JSON; show invalid SMILES producing failure. | “The record can be downloaded. Invalid input produces a clear failure. The application does not turn an unsuccessful run into a simulated result.” |
| 2:15–2:40 | Show limitations and return to overview. | “Judge access is authenticated, and a persistent shared budget bounds model attempts across restarts. The goal is a transparent research brief: calculated evidence, model commentary, and missing evidence kept visible.” |

If the provider call takes longer, trim other narration or visibly label a shortened wait. Total final film must be strictly less than three minutes. Show the actual returned NVIDIA model in the receipt; do not narrate an unverified name.

YouTube draft title: ResistAI Evidence Review | Nebius × NVIDIA Global AI Hackathon  
Description: A working research-software demonstration of RDKit descriptors and NVIDIA Nemotron commentary through Nebius Token Factory. Calculations and unreviewed model commentary are kept separate. No clinical validation. Add only verified public code and demo links after publication.

Release checks: public visibility, playable signed out, duration below 3:00, readable actual interaction, explicit Nebius + NVIDIA usage, no credentials in any frame or audio.
