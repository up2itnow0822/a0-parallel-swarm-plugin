# Tests — DOX

## Purpose

Pytest suite for orchestrator, router, memory, tools, and concurrency.

## Ownership

- `conftest.py` plus `test_*.py` in this directory.

## Local Contracts

- `pytest.ini` is the runner config.
- Install `requirements-dev.txt` before running.

## Work Guidance

- Add tests with behavioral changes; do not skip failures to green CI.

## Verification

- `pytest -q`

## Child DOX Index

- None
