import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from helpers.print_style import PrintStyle
from plugins.parallel_swarm.python.helpers.token_pool import TokenPool
from plugins.parallel_swarm.python.helpers.concurrency import ConcurrencyManager
from plugins.parallel_swarm.python.helpers.swarm_memory import SwarmMemory
from plugins.parallel_swarm.python.helpers import model_router
from plugins.parallel_swarm.python.helpers.model_router import TaskComplexity

if TYPE_CHECKING:
    from agent import Agent


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class SwarmTask:
    id: str
    description: str
    message: str
    complexity: TaskComplexity = TaskComplexity.MODERATE
    profile: str = ""
    priority: int = 0
    dependencies: list[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    result: str | None = None
    error: str | None = None
    token_budget: int = 0
    tokens_used: int = 0
    agent_number: int | None = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    _auto_classified: bool = False


class SwarmOrchestrator:
    """Manages parallel subordinate agent execution.

    Provides fan-out/fan-in execution with:
    - Bounded concurrency via semaphore
    - Token budget management
    - Dynamic model routing by task complexity
    - Task dependency resolution (DAG)
    - Shared memory for federated learning
    """

    def __init__(
        self,
        parent_agent: "Agent",
        max_concurrency: int = 5,
        token_budget: int = 100000,
        per_task_budget: int = 20000,
        auto_classify: bool = True,
    ):
        self.parent_agent = parent_agent
        self.max_concurrency = max_concurrency
        self.auto_classify = auto_classify
        self.token_pool = TokenPool(
            total_budget=token_budget,
            per_task_default=per_task_budget,
        )
        self.concurrency = ConcurrencyManager(max_concurrency=max_concurrency)
        self.memory = SwarmMemory()
        self.tasks: dict[str, SwarmTask] = {}
        self.agents: dict[str, "Agent"] = {}
        self._cancelled = False

    async def dispatch(self, tasks: list[SwarmTask]) -> dict[str, str]:
        """Fan-out: dispatch tasks to parallel subordinates.

        Resolves dependencies, classifies complexity, allocates token budgets,
        creates Agent instances, and executes via asyncio.gather.

        Returns dict of task_id -> result string.
        """

        # Register tasks
        for task in tasks:
            if not task.id:
                task.id = str(uuid.uuid4())[:8]
            self.tasks[task.id] = task

        # Classify complexity if auto-classify enabled
        if self.auto_classify:
            await self._classify_tasks()

        # Call pre-dispatch extensions
        await self.parent_agent.call_extensions(
            "swarm_dispatch_before",
            orchestrator=self,
            tasks=self.tasks,
        )

        # Build dependency DAG and execute in levels
        levels = self._build_execution_levels()
        results: dict[str, str] = {}

        for level_idx, level_tasks in enumerate(levels):
            if self._cancelled:
                break

            PrintStyle(font_color="#4CAF50", bold=True, padding=True).print(
                f"Swarm: Executing level {level_idx} ({len(level_tasks)} tasks)"
            )

            # Execute all tasks in this level concurrently
            coros = [self._execute_task(task) for task in level_tasks]
            level_results = await asyncio.gather(*coros, return_exceptions=True)

            # Process results
            for task, result in zip(level_tasks, level_results):
                if isinstance(result, Exception):
                    task.status = TaskStatus.FAILED
                    task.error = str(result)
                    task.result = f"Error: {str(result)}"
                    results[task.id] = task.result
                    PrintStyle(font_color="red", padding=True).print(
                        f"Swarm task '{task.description}' failed: {str(result)}"
                    )
                else:
                    results[task.id] = str(result) if result else ""

        # Call post-dispatch extensions
        await self.parent_agent.call_extensions(
            "swarm_dispatch_after",
            orchestrator=self,
            results=results,
        )

        return results

    async def _execute_task(self, task: SwarmTask) -> str:
        """Execute a single task in a subordinate agent."""
        from agent import Agent, UserMessage
        from initialize import initialize_agent

        task.status = TaskStatus.RUNNING

        # Allocate tokens from pool
        budget = task.token_budget or self.token_pool.per_task_default
        allocated = await self.token_pool.allocate(task.id, budget)
        if not allocated:
            task.status = TaskStatus.FAILED
            task.error = "Token budget exhausted"
            return "Error: Token budget exhausted for this task."

        # Acquire concurrency slot
        await self.concurrency.acquire()

        try:
            # Initialize config with appropriate model for complexity
            config = initialize_agent()
            task_config = model_router.select_model_config(task.complexity, config)

            # Set profile if provided
            if task.profile:
                task_config.profile = task.profile

            # Create subordinate agent
            agent_number = self.parent_agent.number + 1 + len(self.agents)
            task.agent_number = agent_number
            sub = Agent(agent_number, task_config, self.parent_agent.context)
            sub.set_data(Agent.DATA_NAME_SUPERIOR, self.parent_agent)
            sub.set_data("_swarm_memory", self.memory)
            sub.set_data("_swarm_task_id", task.id)
            self.agents[task.id] = sub

            # Call task start extensions
            await self.parent_agent.call_extensions(
                "swarm_task_start",
                task=task,
                swarm_agent=sub,
            )

            PrintStyle(font_color="#2196F3", padding=True).print(
                f"Swarm A{agent_number}: Starting '{task.description}' "
                f"[{task.complexity.value}]"
            )

            # Add user message and run monologue
            sub.hist_add_user_message(UserMessage(message=task.message, attachments=[]))
            result = await sub.monologue()

            # Seal history topic
            sub.history.new_topic()

            # Update task
            task.status = TaskStatus.COMPLETED
            task.result = result
            task.completed_at = datetime.now()

            # Reconcile token usage
            ctx_data = sub.get_data(Agent.DATA_NAME_CTX_WINDOW) or {}
            task.tokens_used = ctx_data.get("tokens", 0)
            await self.token_pool.consume(task.id, task.tokens_used)

            # Reset throttle on success
            self.concurrency.reset_throttle()

            # Call task complete extensions
            await self.parent_agent.call_extensions(
                "swarm_task_complete",
                task=task,
                result=result,
            )

            PrintStyle(font_color="#4CAF50", padding=True).print(
                f"Swarm A{agent_number}: Completed '{task.description}' "
                f"({task.tokens_used} tokens)"
            )

            return result

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.now()
            self.concurrency.adaptive_throttle("error")
            raise

        finally:
            # Release resources
            await self.token_pool.release(task.id)
            await self.concurrency.release()

    async def cancel_all(self):
        """Cancel all pending/running tasks."""
        self._cancelled = True
        for task in self.tasks.values():
            if task.status in (TaskStatus.PENDING, TaskStatus.RUNNING):
                task.status = TaskStatus.CANCELLED

    def get_status(self) -> dict[str, Any]:
        """Return status of all tasks for orchestrator visibility."""
        return {
            task_id: {
                "description": task.description,
                "status": task.status.value,
                "complexity": task.complexity.value,
                "tokens_used": task.tokens_used,
                "agent_number": task.agent_number,
                "error": task.error,
            }
            for task_id, task in self.tasks.items()
        }

    async def _classify_tasks(self):
        """Classify complexity for tasks marked as auto-classified.

        Only tasks where no explicit complexity was provided by the caller
        (flagged via _auto_classified=True) are reclassified. User-provided
        complexity values are preserved.
        """
        for task in self.tasks.values():
            if not task._auto_classified:
                continue  # user explicitly set complexity — don't touch
            task.complexity = await model_router.classify_complexity(
                task.description,
                self.parent_agent,
                use_llm=self.auto_classify,
            )

    def _build_execution_levels(self) -> list[list[SwarmTask]]:
        """Build dependency DAG and return tasks grouped by execution level.

        Level 0: tasks with no dependencies
        Level 1: tasks depending on level 0
        etc.
        """
        # Validate: no cycles (basic check)
        all_ids = set(self.tasks.keys())
        for task in self.tasks.values():
            for dep in task.dependencies:
                if dep not in all_ids:
                    raise ValueError(
                        f"Task '{task.id}' depends on unknown task '{dep}'"
                    )

        completed: set[str] = set()
        levels: list[list[SwarmTask]] = []
        remaining = dict(self.tasks)

        max_iterations = len(self.tasks) + 1
        iteration = 0

        while remaining:
            iteration += 1
            if iteration > max_iterations:
                unresolved = [t.id for t in remaining.values()]
                raise ValueError(
                    f"Circular dependency detected among tasks: {unresolved}"
                )

            # Find tasks whose dependencies are all completed
            ready = []
            for task_id, task in list(remaining.items()):
                if all(dep in completed for dep in task.dependencies):
                    ready.append(task)
                    del remaining[task_id]

            if not ready and remaining:
                unresolved = [t.id for t in remaining.values()]
                raise ValueError(
                    f"Circular dependency detected among tasks: {unresolved}"
                )

            # Sort by priority within level
            ready.sort(key=lambda t: t.priority)
            levels.append(ready)
            completed.update(t.id for t in ready)

        return levels

    def format_results(self, results: dict[str, str]) -> str:
        """Format all results into a combined response string."""
        if not results:
            return "No tasks were executed."

        parts = []
        for task_id, result in results.items():
            task = self.tasks.get(task_id)
            desc = task.description if task else task_id
            status = task.status.value if task else "unknown"
            parts.append(f"## Task: {desc}\n**Status:** {status}\n\n{result}")

        return "\n\n---\n\n".join(parts)
