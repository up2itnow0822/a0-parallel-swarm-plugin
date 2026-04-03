# Changelog

## [1.0.1] - 2026-04-03

### Added
- **Integration test suite** — 89 tests across 6 test files covering all modules
  - `test_swarm_orchestrator.py` — dispatch, DAG dependency resolution, cancellation, priority sorting
  - `test_token_pool.py` — budget allocation, exhaustion, per-task limits, usage reports
  - `test_concurrency.py` — semaphore blocking, bounded concurrency, adaptive throttle
  - `test_swarm_memory.py` — store/retrieve, tag/keyword queries, federation, concurrent writes
  - `test_model_router.py` — heuristic + LLM classification, model selection by complexity
  - `test_call_swarm_tool.py` — tool execution with mocked Agent Zero runtime
- `tests/conftest.py` — A0 runtime stubs (Agent, Tool, Response, DirtyJson) for standalone testing
- `pytest.ini` and `requirements-dev.txt`
- **Multi-agent example** in README — "Research 5 Markets Simultaneously" with full JSON task array, dependency chain, and expected output format

### Verified
- Agent Zero compatibility check (latest commit, 2026-04): `Tool`, `Response`, `DirtyJson`, `Agent` interfaces all compatible
- `DATA_NAME_SWARM_ORCHESTRATOR` is plugin-defined (not in A0 core) — uses string constant, no conflict

## [1.0.0] - 2026-03-23

### Added
- Initial release
- Parallel Swarm plugin for Agent Zero — run multiple agents concurrently
- Fan-out task execution with bounded concurrency (up to 20 parallel agents)
- Task dependency graphs (DAG support)
- Token budget management with per-task and total caps
- Smart model routing (cheap models for simple tasks, powerful models for complex ones)
- Shared memory for mid-execution agent communication via `swarm_share`
