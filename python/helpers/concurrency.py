import asyncio
import time


class ConcurrencyManager:
    """Traffic management and backpressure control for swarm execution.

    Uses semaphore for bounded parallelism and adaptive throttling
    on rate limit errors.
    """

    def __init__(self, max_concurrency: int = 5, backpressure_threshold: float = 0.8):
        self.max_concurrency = max_concurrency
        self.backpressure_threshold = backpressure_threshold
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._active_count = 0
        self._lock = asyncio.Lock()
        self._throttle_delay: float = 0.0
        self._last_error_time: float = 0.0

    async def acquire(self) -> bool:
        """Acquire a concurrency slot. Blocks until one is available."""
        await self._semaphore.acquire()
        async with self._lock:
            self._active_count += 1
        # Apply throttle delay if we've been hitting rate limits
        if self._throttle_delay > 0:
            await asyncio.sleep(self._throttle_delay)
        return True

    async def release(self):
        """Release a concurrency slot."""
        async with self._lock:
            self._active_count = max(0, self._active_count - 1)
        self._semaphore.release()

    async def get_active_count(self) -> int:
        """Number of currently active tasks."""
        async with self._lock:
            return self._active_count

    async def get_available_slots(self) -> int:
        """Number of available concurrency slots."""
        async with self._lock:
            return self.max_concurrency - self._active_count

    def adaptive_throttle(self, error_type: str = "rate_limit"):
        """Increase delay on rate limit errors. Call on transient errors."""
        now = time.time()
        if now - self._last_error_time < 5:
            # Multiple errors in quick succession — increase throttle
            self._throttle_delay = min(self._throttle_delay * 2 + 0.5, 30.0)
        else:
            self._throttle_delay = 0.5
        self._last_error_time = now

    def reset_throttle(self):
        """Reset throttle delay after successful operation."""
        self._throttle_delay = max(0, self._throttle_delay - 0.1)

    async def resource_check(self, token_pool=None) -> bool:
        """Verify system has capacity for more agents."""
        async with self._lock:
            if self._active_count >= self.max_concurrency:
                return False
        if token_pool:
            remaining = await token_pool.get_remaining()
            if remaining <= 0:
                return False
        return True
