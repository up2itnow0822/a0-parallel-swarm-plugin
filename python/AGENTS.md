# Python runtime — DOX

## Purpose

Plugin helpers, agent init, orchestration, routing, and memory used by Agent Zero at runtime.

## Ownership

- `agent_init/` — plugin startup
- `helpers/` — swarm orchestration, routing, budgets, memory

## Local Contracts

- Public helpers must stay importable from the plugin package layout described in `README.md`.

## Work Guidance

- Preserve token-budget and concurrency invariants when changing orchestration.

## Verification

- Covered by `tests/` and CI `validate`.

## Child DOX Index

- None
