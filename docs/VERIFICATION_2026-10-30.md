# ResistAI publication verification

Verified October 30, 2026, after the initial local readiness record.

## Published work

- Draft pull request: https://github.com/k2jac9/resist-ai/pull/15
- Branch: `fix/nebius-evidence-integrity-20261030`
- Baseline: `95dc342b1420c6287c7e4f0544b7c4a002cab583`
- Implementation head: `be224c063a7421e468d846003c14ffae52ae3868`
- Implementation tree: `8b07ed6032c2f792c3f9d29e3ae587940c64d120`
- The 25 implementation/documentation file blobs matched the tested local copies. Reconstructing the expected tree from local Git blob hashes and the unchanged baseline produced exactly that tree SHA.
- This verification record and plan completion note are a documentation-only follow-up. They do not change implementation code.

## Full-repository CI passed

Workflow: https://github.com/k2jac9/resist-ai/actions/runs/41006212367

The workflow checked out the complete PR merge ref `7327542edefcee275a0af991f49a05b7f0999c60`, combining implementation head with the unchanged baseline. It used CPython **3.11.17**, installed `requirements-dev.txt` including the repository's pinned runtime requirements, and completed both jobs successfully.

| Check | Observed result |
|---|---|
| Ruff lint | Passed, job `123901585032` |
| Compile every tracked Python file | Passed |
| Full `pytest -q` | **342 passed in 2.47s**, job `123901585311` |

The test job completed at 05:03:15 UTC. Its decoded log was read and the test count verified. The workflow emitted infrastructure warnings about a concurrent pip-cache save and older Node-targeted action versions; these did not fail the lint or test jobs.

This closes the initial full-repository CI execution gate for the implementation head. It does not turn offline tests into provider or scientific validation. The earlier record's local test count of 116 remains correct for the sparse local overlay.

## Still not established

No successful live Nebius or NVIDIA biology inference, hosted judge-access acceptance, browser-pixel review, Docker qualification, independent code/scientific review, public repository/license approval, video upload or submission confirmation. Main remains unchanged and the PR remains draft. The original Team BioHack copyright/license status is preserved.

The highest-leverage next gate is to configure the Nebius credential outside source control and execute `python scripts/smoke_nebius.py --smiles CCO --output /tmp/resistai-nebius-smoke.json`, then inspect the actual returned model identity and commentary. The software fixture is not a treatment candidate. The deeper legacy pipeline remains explicitly unverified until its input identities, metric semantics and per-stage provenance are repaired.
