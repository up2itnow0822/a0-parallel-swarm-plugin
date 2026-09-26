# GitHub Actions — DOX

## Purpose

CI, required `build` status, and release bundling for the plugin.

## Ownership

- `workflows/ci.yml` — matrix validate (compile + pytest)
- `workflows/build.yml` — required `build` job for the default-branch ruleset
- `workflows/release.yml` — tagged plugin zip

## Local Contracts

- The required status check name is `build`.
- Python paths must run compile and tests as separate steps; a test failure must fail the job.
- Do not `||` a succeeding compile over a failing pytest.

## Work Guidance

- Detect Node / Python / Rust / Go / Makefile only when those manifests exist.
- Keep this repo's path aligned with `ci.yml`: install `requirements-dev.txt`, compile, then pytest.

## Verification

- `build` and `validate` must be green on the PR head.

## Child DOX Index

- None
