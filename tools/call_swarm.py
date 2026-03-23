from python.helpers.tool import Tool, Response
from plugins.parallel_swarm.python.helpers.swarm import SwarmOrchestrator, SwarmTask, TaskStatus
from plugins.parallel_swarm.python.helpers.model_router import TaskComplexity
from python.helpers import dirty_json
from agent import Agent


class SwarmDelegation(Tool):
    """Dispatch multiple tasks to subordinate agents in parallel."""

    async def execute(self, tasks="", max_concurrency=0, token_budget=0, **kwargs):
        config = self.agent.config

        if not config.swarm_enabled:
            return Response(
                message="Swarm mode is disabled in settings.",
                break_loop=False,
            )

        # Parse tasks from JSON string
        task_list = dirty_json.DirtyJson.parse_string(str(tasks))
        if not task_list or not isinstance(task_list, list):
            return Response(
                message="Error: 'tasks' must be a JSON array of task objects. "
                "Each object needs at least 'description' and 'message' fields.",
                break_loop=False,
            )

        # Build SwarmTask objects
        swarm_tasks = []
        for i, t in enumerate(task_list):
            if not isinstance(t, dict):
                continue

            # Parse complexity if provided
            complexity = TaskComplexity.MODERATE
            complexity_str = str(t.get("complexity", "")).lower()
            if complexity_str == "simple":
                complexity = TaskComplexity.SIMPLE
            elif complexity_str == "complex":
                complexity = TaskComplexity.COMPLEX

            task = SwarmTask(
                id=str(t.get("id", f"task_{i}")),
                description=t.get("description", f"Task {i}"),
                message=t.get("message", t.get("description", "")),
                complexity=complexity,
                profile=t.get("profile", ""),
                priority=int(t.get("priority", 0)),
                dependencies=t.get("depends_on", []) or [],
                token_budget=int(t.get("token_budget", 0)),
            )
            swarm_tasks.append(task)

        if not swarm_tasks:
            return Response(
                message="Error: No valid tasks found in the provided list.",
                break_loop=False,
            )

        # Create orchestrator
        concurrency = int(max_concurrency) if max_concurrency else config.swarm_max_concurrency
        budget = int(token_budget) if token_budget else config.swarm_token_budget
        orchestrator = SwarmOrchestrator(
            parent_agent=self.agent,
            max_concurrency=concurrency,
            token_budget=budget,
            per_task_budget=config.swarm_per_task_budget,
            auto_classify=config.swarm_auto_classify,
        )

        # Store reference on agent
        self.agent.set_data(Agent.DATA_NAME_SWARM_ORCHESTRATOR, orchestrator)

        # Dispatch and collect results
        results = await orchestrator.dispatch(swarm_tasks)

        # Format combined response
        formatted = orchestrator.format_results(results)

        # Get usage report for logging
        usage = await orchestrator.token_pool.get_usage_report()

        # Summary line
        completed = sum(1 for t in orchestrator.tasks.values() if t.status == TaskStatus.COMPLETED)
        failed = sum(1 for t in orchestrator.tasks.values() if t.status == TaskStatus.FAILED)
        total = len(orchestrator.tasks)
        summary = f"\n\n---\n**Swarm Summary:** {completed}/{total} tasks completed"
        if failed:
            summary += f", {failed} failed"
        summary += f" | Total tokens consumed: {usage['total_consumed']}"

        return Response(
            message=formatted + summary,
            break_loop=False,
        )

    def get_log_object(self):
        return self.agent.context.log.log(
            type="subagent",
            heading=f"icon://hub {self.agent.agent_name}: Dispatching Swarm Tasks",
            content="",
            kvps=self.args,
        )
