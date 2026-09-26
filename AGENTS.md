# Parallel Swarm Plugin — DOX

## Purpose

Agent Zero plugin that fans out concurrent subordinate agents with DAG dependencies, token budgets, shared memory, and model routing.

## Ownership

- Owner: Agent Economy, LLC (`@up2itnow0822`)
- Runtime code: `python/`, `tools/`, `webui/`
- Verification: `tests/`, `.github/workflows/`

## Local Contracts

- Plugin manifest is `plugin.yaml`; install layout is described in `README.md`.
- Python 3.11+; test extras live in `requirements-dev.txt`.
- Do not swallow CI/test failures behind fallbacks that report success.

## Work Guidance

- Keep plugin surfaces (tools, settings, memory) compatible with Agent Zero's plugin contract.
- Prefer targeted tests over broad refactors when remediating review findings.

## Verification

- Local: `python -m pip install -r requirements-dev.txt && pytest -q`
- CI: `.github/workflows/ci.yml` (`validate`) and `.github/workflows/build.yml` (`build`)

## Child DOX Index

- `.github/AGENTS.md` — Actions workflows and required status checks
- `python/AGENTS.md` — plugin runtime helpers and agent init
- `tools/AGENTS.md` — Agent Zero tool entrypoints
- `webui/AGENTS.md` — plugin UI
- `tests/AGENTS.md` — pytest suite
