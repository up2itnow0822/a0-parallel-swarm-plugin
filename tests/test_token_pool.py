"""Tests for TokenPool — budget allocation, exhaustion, per-task limits."""

import pytest
from plugins.parallel_swarm.python.helpers.token_pool import TokenPool


class TestTokenPoolAllocation:
    async def test_allocate_within_budget(self, token_pool):
        result = await token_pool.allocate("t1", 10000)
        assert result is True
        remaining = await token_pool.get_remaining()
        assert remaining == 90000

    async def test_allocate_uses_default_budget(self, token_pool):
        result = await token_pool.allocate("t1", 0)
        assert result is True
        remaining = await token_pool.get_remaining()
        assert remaining == 80000  # 100k - 20k default

    async def test_allocate_multiple_tasks(self, token_pool):
        await token_pool.allocate("t1", 20000)
        await token_pool.allocate("t2", 30000)
        remaining = await token_pool.get_remaining()
        assert remaining == 50000

    async def test_allocate_exceeds_budget_returns_false(self, token_pool):
        await token_pool.allocate("t1", 80000)
        result = await token_pool.allocate("t2", 30000)
        assert result is False

    async def test_allocate_exactly_at_budget(self, token_pool):
        result = await token_pool.allocate("t1", 100000)
        assert result is True
        result = await token_pool.allocate("t2", 1)
        assert result is False


class TestTokenPoolConsumption:
    async def test_consume_tracks_usage(self, token_pool):
        await token_pool.allocate("t1", 20000)
        await token_pool.consume("t1", 5000)
        consumed = await token_pool.get_consumed()
        assert consumed == 5000

    async def test_consume_multiple_increments(self, token_pool):
        await token_pool.allocate("t1", 20000)
        await token_pool.consume("t1", 3000)
        await token_pool.consume("t1", 2000)
        consumed = await token_pool.get_consumed()
        assert consumed == 5000

    async def test_is_task_over_budget(self, token_pool):
        await token_pool.allocate("t1", 1000)
        await token_pool.consume("t1", 1000)
        assert await token_pool.is_task_over_budget("t1") is True

    async def test_is_task_under_budget(self, token_pool):
        await token_pool.allocate("t1", 1000)
        await token_pool.consume("t1", 500)
        assert await token_pool.is_task_over_budget("t1") is False

    async def test_task_budget_remaining(self, token_pool):
        await token_pool.allocate("t1", 10000)
        await token_pool.consume("t1", 3000)
        remaining = await token_pool.get_task_budget_remaining("t1")
        assert remaining == 7000

    async def test_nonexistent_task_budget_remaining(self, token_pool):
        remaining = await token_pool.get_task_budget_remaining("nope")
        assert remaining == 0


class TestTokenPoolRelease:
    async def test_release_frees_budget(self, token_pool):
        await token_pool.allocate("t1", 50000)
        consumed = await token_pool.release("t1")
        remaining = await token_pool.get_remaining()
        assert remaining == 100000
        assert consumed == 0

    async def test_release_returns_consumed(self, token_pool):
        await token_pool.allocate("t1", 20000)
        await token_pool.consume("t1", 7500)
        consumed = await token_pool.release("t1")
        assert consumed == 7500

    async def test_release_nonexistent_task(self, token_pool):
        consumed = await token_pool.release("nope")
        assert consumed == 0


class TestTokenPoolReport:
    async def test_usage_report_structure(self, token_pool):
        await token_pool.allocate("t1", 10000)
        await token_pool.consume("t1", 3000)
        report = await token_pool.get_usage_report()
        assert report["total_budget"] == 100000
        assert report["total_allocated"] == 10000
        assert report["total_consumed"] == 3000
        assert "t1" in report["tasks"]
        assert report["tasks"]["t1"]["budget"] == 10000
        assert report["tasks"]["t1"]["consumed"] == 3000
        assert report["tasks"]["t1"]["over_budget"] is False

    async def test_reset_clears_all(self, token_pool):
        await token_pool.allocate("t1", 50000)
        await token_pool.reset()
        remaining = await token_pool.get_remaining()
        assert remaining == 100000
