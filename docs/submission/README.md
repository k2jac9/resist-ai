# Nebius hackathon submission package

Candidate: **ResistAI: Evidence-First Research Copilot**  
Track: **Best Apps and Agents**  
Deadline: October 30, 2026, 10:00 AM Pacific / 1:00 PM Toronto / 17:00 UTC.

This package is a release candidate, not proof that the project has been submitted. It builds on the existing private Team BioHack repository. See [release status](RELEASE_STATUS.md), [Devpost draft](DEVPOST.md), [video script](VIDEO_SCRIPT.md), and [feedback worksheet](FEEDBACK.md).

## Run the dedicated judge application

Python 3.11:

```bash
python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-submission.txt
mkdir -p data
export RESISTAI_QUOTA_DB="$(pwd)/data/attempts.sqlite3"
export RESISTAI_UI_USER=judge
read -rs -p "Judge password (at least 16 characters): " RESISTAI_UI_PASSWORD
export RESISTAI_UI_PASSWORD
read -rs -p "Nebius API key: " NEBIUS_API_KEY
export NEBIUS_API_KEY
export NEBIUS_BASE_URL=https://api.tokenfactory.us-central1.nebius.com/v1
export NEBIUS_MODEL=nvidia/nemotron-3-super-120b-a12b
python -m src.submission_app
```

Open http://127.0.0.1:7860 and authenticate. These instructions do not write secrets to a tracked file. The dedicated profile uses process environment variables, not automatic .env loading. It intentionally refuses startup without judge authentication, a provider key, and an absolute writable quota database path. The legacy no-auth switch does not apply.

For a container:

```bash
docker build -f Dockerfile.submission -t resistai-evidence .
docker volume create resistai-evidence-data
docker run --rm -p 127.0.0.1:7860:7860 \
  --mount source=resistai-evidence-data,target=/data \
  -e NEBIUS_API_KEY -e NEBIUS_BASE_URL -e NEBIUS_MODEL \
  -e RESISTAI_UI_USER -e RESISTAI_UI_PASSWORD \
  resistai-evidence
```

## Hosting contract

Deploy this Dockerfile behind managed HTTPS, use one replica, and attach a persistent volume at /data writable by UID/GID 10001. Do not deploy with ephemeral storage or multiple independent volumes: those reset or multiply the application budget. The database contains timestamps and counts, not molecules or API keys. Preserve it across releases. Do not expose the legacy app or REST API as part of this profile.

Set the variables above in the hosting service's secret configuration. PORT defaults to 7860 and respects the host-provided value. A minimal /healthz endpoint is public; the interface and review endpoint require HTTP Basic authentication. Provide the judge credentials only in the submission's private testing instructions, never in the public README or video. Authenticated users can spend the shared quota; this is not per-person isolation.

Default global limits are 4 model attempts in any rolling 60 seconds, 40 in a rolling 24 hours, and 200 over this database's lifetime. Override with positive integer RESISTAI_MODEL_PER_MINUTE, RESISTAI_MODEL_PER_DAY, and RESISTAI_MODEL_LIFETIME. Failed attempts count. Descriptor-only requests do not consume model attempts. These are request admission limits, not an account-wide dollar cap. Configure provider spending controls separately and inspect actual account pricing before increasing limits.

The transport requests at most 2,048 output tokens for this workflow, does not retry, and uses bounded per-operation HTTP timeouts. A receipt records observed provider metadata, not a cryptographic attestation. Keep the service accessible through the official judging window, December 9–23, 2026; verify that date against the event page before release.

## Judge acceptance procedure

1. Use an unauthenticated session: /healthz returns only status, / and POST /api/review require authentication, and /docs, /openapi.json and file-serving paths are absent.
2. Authenticate, leave model opt-in off, and review CCO. Inspect actual RDKit values, version, canonical structure fingerprint, and model_status=not_requested.
3. Select model review and run once. Require model_status=response_received and a receipt identifying the actual Nebius endpoint, requested and returned NVIDIA model, elapsed time and any provided usage/request ID. Inspect commentary for unsupported claims; schema validation alone is insufficient.
4. Download the JSON record. Confirm secrets are absent and the file came from that displayed run.
5. Submit an invalid SMILES and verify a visible failure with no replacement result.
6. Exercise a provider-unavailable case in a controlled staging configuration; verify calculated evidence remains labeled separately and unavailable is explicit. Never use staging fixtures as live inference evidence.
7. Restart the service and verify that reservations persist. Confirm quotas cannot be bypassed through direct API requests.
8. Record the actual workflow, keep the film below three minutes, publish it publicly on YouTube, and open it signed out.
9. Check the demo HTTPS URL signed out and then with judge credentials. Retain the deployment revision and a sanitized real response record.

## Verification

```bash
python -m pip install -r requirements-dev.txt
ruff check src/ tests/ scripts/
python -m pytest -q
```

Provider integration tests use controlled responses. Only the hosted acceptance run establishes actual model usage. Never put API keys, passwords, raw account screens, or unreleased teammate information into the repository, JSON evidence, video, or public form.
