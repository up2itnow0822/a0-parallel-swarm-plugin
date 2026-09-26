# Tools — DOX

## Purpose

Agent Zero tool entrypoints (`call_swarm`, `swarm_share`, and related).

## Ownership

- Files in this directory are the agent-facing tool surface.

## Local Contracts

- Tool names and argument shapes must remain compatible with existing agent prompts.

## Work Guidance

- Keep tool adapters thin; put orchestration in `python/helpers`.

## Verification

- `tests/test_call_swarm_tool.py` and related suite.

## Child DOX Index

- None
