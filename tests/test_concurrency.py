"""Tests for ConcurrencyManager — semaphore limiting, bounded concurrency."""

import asyncio
import pytest
from plugins.parallel_swarm.python.helpers.concurrency import ConcurrencyManager


class TestConcurrencyAcquireRelease:
    async def test_acquire_increments_active(self, concurrency_manager):
        await concurrency_manager.acquire()
        count = await concurrency_manager.get_active_count()
        assert count == 1
        await concurrency_manager.release()

    async def test_release_decrements_active(self, concurrency_manager):
        await concurrency_manager.acquire()
        await concurrency_manager.release()
        count = await concurrency_manager.get_active_count()
        assert count == 0

    async def test_available_slots_decreases(self, concurrency_manager):
        initial = await concurrency_manager.get_available_slots()
        assert initial == 3
        await concurrency_manager.acquire()
        slots = await concurrency_manager.get_available_slots()
        assert slots == 2
        await concurrency_manager.release()

    async def test_release_below_zero_clamps(self, concurrency_manager):
        await concurrency_manager.release()
        count = await concurrency_manager.get_active_count()
        assert count == 0


class TestBoundedConcurrency:
    async def test_semaphore_blocks_at_limit(self, concurrency_manager):
        """Verify that acquiring beyond max_concurrency blocks."""
        # Acquire all 3 slots
        for _ in range(3):
            await concurrency_manager.acquire()

        # 4th acquire should block — use wait_for to prove it
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(concurrency_manager.acquire(), timeout=0.1)

        # Clean up
        for _ in range(3):
            await concurrency_manager.release()

    async def test_release_unblocks_waiter(self, concurrency_manager):
        """After release, a blocked acquire proceeds."""
        for _ in range(3):
            await concurrency_manager.acquire()

        acquired = asyncio.Event()

        async def waiter():
            await concurrency_manager.acquire()
            acquired.set()

        task = asyncio.create_task(waiter())
        await asyncio.sleep(0.05)
        assert not acquired.is_set()

        await concurrency_manager.release()
        await asyncio.wait_for(acquired.wait(), timeout=1.0)
        assert acquired.is_set()

        # Clean up
        for _ in range(3):
            await concurrency_manager.release()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


class TestAdaptiveThrottle:
    async def test_throttle_sets_delay(self, concurrency_manager):
        assert concurrency_manager._throttle_delay == 0.0
        concurrency_manager.adaptive_throttle("rate_limit")
        assert concurrency_manager._throttle_delay == 0.5

    async def test_rapid_errors_increase_throttle(self, concurrency_manager):
        concurrency_manager.adaptive_throttle("rate_limit")
        first = concurrency_manager._throttle_delay
        concurrency_manager.adaptive_throttle("rate_limit")
        second = concurrency_manager._throttle_delay
        assert second > first

    async def test_reset_throttle_decreases_delay(self, concurrency_manager):
        concurrency_manager._throttle_delay = 2.0
        concurrency_manager.reset_throttle()
        assert concurrency_manager._throttle_delay < 2.0

    async def test_reset_throttle_floors_at_zero(self, concurrency_manager):
        concurrency_manager._throttle_delay = 0.05
        concurrency_manager.reset_throttle()
        assert concurrency_manager._throttle_delay == 0.0


class TestResourceCheck:
    async def test_resource_check_when_available(self, concurrency_manager):
        result = await concurrency_manager.resource_check()
        assert result is True

    async def test_resource_check_at_capacity(self, concurrency_manager):
        for _ in range(3):
            await concurrency_manager.acquire()
        result = await concurrency_manager.resource_check()
        assert result is False
        for _ in range(3):
            await concurrency_manager.release()

    async def test_resource_check_with_token_pool(self, concurrency_manager, token_pool):
        result = await concurrency_manager.resource_check(token_pool=token_pool)
        assert result is True

    async def test_resource_check_exhausted_tokens(self, concurrency_manager, token_pool):
        await token_pool.allocate("t1", 100000)
        result = await concurrency_manager.resource_check(token_pool=token_pool)
        assert result is False
        await token_pool.release("t1")
