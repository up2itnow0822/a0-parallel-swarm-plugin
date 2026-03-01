import asyncio
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TaskAllocation:
    task_id: str
    budget: int
    consumed: int = 0
    allocated_at: float = field(default_factory=time.time)


class TokenPool:
    """Centralized token budget manager for swarm parallel execution.

    Enforces a total token budget across all parallel agents.
    Uses pre-allocation to prevent runaway costs.
    """

    def __init__(self, total_budget: int = 100000, per_task_default: int = 20000):
        self.total_budget = total_budget
        self.per_task_default = per_task_default
        self.allocations: dict[str, TaskAllocation] = {}
        self._lock = asyncio.Lock()

    async def allocate(self, task_id: str, budget: int = 0) -> bool:
        """Reserve tokens for a task. Returns False if over budget."""
        budget = budget or self.per_task_default
        async with self._lock:
            current_allocated = sum(a.budget for a in self.allocations.values())
            if current_allocated + budget > self.total_budget:
                return False
            self.allocations[task_id] = TaskAllocation(
                task_id=task_id,
                budget=budget,
            )
            return True

    async def consume(self, task_id: str, tokens: int):
        """Record actual token usage during streaming."""
        async with self._lock:
            alloc = self.allocations.get(task_id)
            if alloc:
                alloc.consumed += tokens

    async def release(self, task_id: str) -> int:
        """Free allocation when task completes. Returns tokens consumed."""
        async with self._lock:
            alloc = self.allocations.pop(task_id, None)
            return alloc.consumed if alloc else 0

    async def get_remaining(self) -> int:
        """Total remaining budget (total - allocated)."""
        async with self._lock:
            current_allocated = sum(a.budget for a in self.allocations.values())
            return self.total_budget - current_allocated

    async def get_consumed(self) -> int:
        """Total tokens actually consumed across all tasks."""
        async with self._lock:
            return sum(a.consumed for a in self.allocations.values())

    async def is_task_over_budget(self, task_id: str) -> bool:
        """Check if a specific task has exceeded its allocation."""
        async with self._lock:
            alloc = self.allocations.get(task_id)
            if not alloc:
                return False
            return alloc.consumed >= alloc.budget

    async def get_task_budget_remaining(self, task_id: str) -> int:
        """Get remaining budget for a specific task."""
        async with self._lock:
            alloc = self.allocations.get(task_id)
            if not alloc:
                return 0
            return max(0, alloc.budget - alloc.consumed)

    async def get_usage_report(self) -> dict[str, Any]:
        """Per-task token consumption summary."""
        async with self._lock:
            tasks = {}
            total_consumed = 0
            total_allocated = 0
            for task_id, alloc in self.allocations.items():
                tasks[task_id] = {
                    "budget": alloc.budget,
                    "consumed": alloc.consumed,
                    "remaining": max(0, alloc.budget - alloc.consumed),
                    "over_budget": alloc.consumed >= alloc.budget,
                }
                total_consumed += alloc.consumed
                total_allocated += alloc.budget
            return {
                "total_budget": self.total_budget,
                "total_allocated": total_allocated,
                "total_consumed": total_consumed,
                "total_remaining": self.total_budget - total_allocated,
                "tasks": tasks,
            }

    async def reset(self):
        """Clear all allocations."""
        async with self._lock:
            self.allocations.clear()
