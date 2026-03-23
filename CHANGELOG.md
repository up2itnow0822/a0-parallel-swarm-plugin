# Changelog

## [1.0.0] - 2026-03-23

### Added
- Initial release
- Parallel Swarm plugin for Agent Zero — run multiple agents concurrently
- Fan-out task execution with bounded concurrency (up to 20 parallel agents)
- Task dependency graphs (DAG support)
- Token budget management with per-task and total caps
- Smart model routing (cheap models for simple tasks, powerful models for complex ones)
- Shared memory for mid-execution agent communication via `swarm_share`
