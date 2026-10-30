# Release status

Verified October 30, 2026. **Not submitted. No hosted demo or live-provider receipt has been verified.**

This record supersedes the earlier pending-CI status for implementation commit `fbb11f9303755be56eba30711e357342c774b9a8`. The update containing this document changes documentation only; its check results are separate from the verified implementation run below.

## Published release and verification

- Draft PR: https://github.com/k2jac9/resist-ai/pull/15
- Branch: `fix/nebius-evidence-integrity-20261030`
- Implementation commit: `fbb11f9303755be56eba30711e357342c774b9a8`
- Implementation tree: `b7ae5d0a40c3dcabd22729c6b3079a9f2c31cd48`
- Tested PR merge ref: `6aa499c26a92d97de6d200513f6429f4dd98ca20`
- CI run: https://github.com/k2jac9/resist-ai/actions/runs/41019726922

All three jobs completed successfully:

| Job | Verified result |
| --- | --- |
| test (`123944052578`) | Full `pytest -q`: **365 passed in 3.51s**. The decoded job log was read. CPython 3.11.17; repository requirements installed. Tracked Python files also passed compilation. |
| lint (`123944052455`) | Ruff lint passed. |
| submission-container (`123944052262`) | Focused submission Docker image built; container authentication and real-descriptor smoke test passed. |

The dedicated submission interface is FastAPI with a small HTML/JavaScript page, not the earlier Gradio-only profile. It requires authentication, limits request bodies and concurrent work, persists model-attempt counts in SQLite, and supports browser-side JSON download. The legacy biological pipeline is not exposed by this application. CI provider responses are controlled test inputs and do not establish a successful live Nebius request, scientific validity, or hosted acceptance.

## Current release gates

| Requirement | Status |
| --- | --- |
| Focused application and model adapter | Published on release branch |
| Persistent request admission | Tested; included in full CI |
| Full pinned-dependency CI and container smoke | Passed for implementation commit identified above |
| Actual Nebius + NVIDIA inference | Blocked: API key not configured in the execution environment; successful response and returned model still required |
| Authenticated HTTPS judge demo | Blocked: Railway project creation was attempted, but the connected account returned that its trial has expired and a plan is required. No project or deployment was created by that attempt. No paid plan was selected. |
| Browser automation | TinyFish tools are now available; its Default profile has no recorded signed-in sites. Devpost/YouTube account access is not established. A secure sign-in setup needs the user's approval. |
| Public repository and visible open-source license | Pending source-distribution authority and license selection; current repository remains private with Team BioHack ownership notice |
| Public working-demo video under 3 minutes | Script prepared; actual live recording and YouTube publication remain pending |
| Specific technology feedback | Draft worksheet exists; measured live observations remain pending |
| Team membership and invitations | Actual participants and accepted invitations remain unverified |
| Devpost submission and confirmation | Not performed; no submitted-entry receipt exists in this work record |

Main is unchanged. PR remains draft. Do not interpret successful offline checks or installed plugins as completed deployment, authentication, live inference, or submission.

## Minimum external inputs

1. An active hosting account/project with approved charges, or an existing suitable host. The attempted Railway project could not be created because its trial expired.
2. `NEBIUS_API_KEY` stored in the trusted deployment environment or secret manager, not in chat, source control, or public form fields. Use separate judge credentials and persistent storage mounted at `/data`, writable by UID/GID 10001.
3. Secure Devpost sign-in, and YouTube access for publishing the real demonstration. Never request or put account passwords in chat.
4. Confirmation of authority to distribute the inherited Team BioHack code under the chosen open-source license, plus the actual submission team. License selection alone does not establish other contributors' permission.

## Execution order after access is available

Deploy the already-tested commit with the documented environment and persistent volume. Verify unauthorized access is rejected. Make a real opt-in model request and retain its sanitized provider receipt; inspect the returned model and generated commentary. Check JSON export and failure behavior in the hosted app. Verify the public licensed source and setup instructions. Record and publish the actual working flow, complete the prepared Devpost draft and measured feedback, verify invitations, and retain the submitted-entry confirmation. Do not claim final submission until that confirmation is observed.

## Deadline and judging window

Official rules rechecked October 30, 2026:

- Submission deadline: **October 30, 2026, 10:00 AM PDT / 1:00 PM EDT (Toronto) / 17:00 UTC**.
- Judging: **December 9-23, 2026**. Keep the accepted demo accessible through the judging period.
- A runtime Token Factory call can satisfy the Nebius platform requirement; at least one qualifying NVIDIA open-source model is still required.
- The project needs a working demo/test-build URL, public licensed source, public YouTube demonstration and the required submission fields. Earlier-project reuse must be disclosed.

Source: https://nebiusglobalaihackathon.devpost.com/rules

## Package references

- [Deployment and judge instructions](README.md)
- [Devpost draft](DEVPOST.md)
- [Video script](VIDEO_SCRIPT.md)
- [Feedback worksheet](FEEDBACK.md)

The prior portfolio assessment is background, not a substitute for this exact-commit release evidence. Existing product names, data labels and legacy scientific scores must not be promoted to validated research results.
