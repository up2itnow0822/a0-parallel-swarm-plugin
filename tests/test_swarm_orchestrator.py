"""Tests for SwarmOrchestrator — dispatch, dependency resolution, cancellation."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from plugins.parallel_swarm.python.helpers.swarm import (
    SwarmOrchestrator,
    SwarmTask,
    TaskStatus,
)
from plugins.parallel_swarm.python.helpers.model_router import TaskComplexity


class TestDependencyResolution:
    def test_no_dependencies_single_level(self, mock_agent):
        orch = SwarmOrchestrator(mock_agent, auto_classify=False)
        t1 = SwarmTask(id="a", description="A", message="do A")
        t2 = SwarmTask(id="b", description="B", message="do B")
        orch.tasks = {"a": t1, "b": t2}
        levels = orch._build_execution_levels()
        assert len(levels) == 1
        assert set(t.id for t in levels[0]) == {"a", "b"}

    def test_linear_dependency_chain(self, mock_agent):
        orch = SwarmOrchestrator(mock_agent, auto_classify=False)
        t1 = SwarmTask(id="a", description="A", message="do A")
        t2 = SwarmTask(id="b", description="B", message="do B", dependencies=["a"])
        t3 = SwarmTask(id="c", description="C", message="do C", dependencies=["b"])
        orch.tasks = {"a": t1, "b": t2, "c": t3}
        levels = orch._build_execution_levels()
        assert len(levels) == 3
        assert levels[0][0].id == "a"
        assert levels[1][0].id == "b"
        assert levels[2][0].id == "c"

    def test_diamond_dependency(self, mock_agent):
        orch = SwarmOrchestrator(mock_agent, auto_classify=False)
        t1 = SwarmTask(id="a", description="A", message="m")
        t2 = SwarmTask(id="b", description="B", message="m", dependencies=["a"])
        t3 = SwarmTask(id="c", description="C", message="m", dependencies=["a"])
        t4 = SwarmTask(id="d", description="D", message="m", dependencies=["b", "c"])
        orch.tasks = {"a": t1, "b": t2, "c": t3, "d": t4}
        levels = orch._build_execution_levels()
        assert len(levels) == 3
        assert levels[0][0].id == "a"
        assert set(t.id for t in levels[1]) == {"b", "c"}
        assert levels[2][0].id == "d"

    def test_circular_dependency_raises(self, mock_agent):
        orch = SwarmOrchestrator(mock_agent, auto_classify=False)
        t1 = SwarmTask(id="a", description="A", message="m", dependencies=["b"])
        t2 = SwarmTask(id="b", description="B", message="m", dependencies=["a"])
        orch.tasks = {"a": t1, "b": t2}
        with pytest.raises(ValueError, match="Circular dependency"):
            orch._build_execution_levels()

    def test_unknown_dependency_raises(self, mock_agent):
        orch = SwarmOrchestrator(mock_agent, auto_classify=False)
        t1 = SwarmTask(id="a", description="A", message="m", dependencies=["z"])
        orch.tasks = {"a": t1}
        with pytest.raises(ValueError, match="unknown task"):
            orch._build_execution_levels()

    def test_priority_sorting_within_level(self, mock_agent):
        orch = SwarmOrchestrator(mock_agent, auto_classify=False)
        t1 = SwarmTask(id="a", description="A", message="m", priority=2)
        t2 = SwarmTask(id="b", description="B", message="m", priority=0)
        t3 = SwarmTask(id="c", description="C", message="m", priority=1)
        orch.tasks = {"a": t1, "b": t2, "c": t3}
        levels = orch._build_execution_levels()
        ids = [t.id for t in levels[0]]
        assert ids == ["b", "c", "a"]


class TestCancellation:
    async def test_cancel_marks_pending_tasks(self, mock_agent):
        orch = SwarmOrchestrator(mock_agent, auto_classify=False)
        t1 = SwarmTask(id="a", description="A", message="m")
        t2 = SwarmTask(id="b", description="B", message="m")
        orch.tasks = {"a": t1, "b": t2}
        await orch.cancel_all()
        assert t1.status == TaskStatus.CANCELLED
        assert t2.status == TaskStatus.CANCELLED
        assert orch._cancelled is True

    async def test_cancel_skips_completed(self, mock_agent):
        orch = SwarmOrchestrator(mock_agent, auto_classify=False)
        t1 = SwarmTask(id="a", description="A", message="m", status=TaskStatus.COMPLETED)
        orch.tasks = {"a": t1}
        await orch.cancel_all()
        assert t1.status == TaskStatus.COMPLETED


class TestGetStatus:
    def test_status_report(self, mock_agent):
        orch = SwarmOrchestrator(mock_agent, auto_classify=False)
        t = SwarmTask(id="a", description="Test", message="m", complexity=TaskComplexity.SIMPLE)
        t.status = TaskStatus.COMPLETED
        t.tokens_used = 500
        t.agent_number = 1
        orch.tasks = {"a": t}
        status = orch.get_status()
        assert status["a"]["status"] == "completed"
        assert status["a"]["complexity"] == "simple"
        assert status["a"]["tokens_used"] == 500


class TestFormatResults:
    def test_format_empty(self, mock_agent):
        orch = SwarmOrchestrator(mock_agent, auto_classify=False)
        assert orch.format_results({}) == "No tasks were executed."

    def test_format_with_results(self, mock_agent):
        orch = SwarmOrchestrator(mock_agent, auto_classify=False)
        t = SwarmTask(id="a", description="Research BTC", message="m", status=TaskStatus.COMPLETED)
        orch.tasks = {"a": t}
        result = orch.format_results({"a": "BTC is at 60k"})
        assert "Research BTC" in result
        assert "BTC is at 60k" in result
        assert "completed" in result


class TestDispatch:
    """Test dispatch with mocked _execute_task to avoid Agent Zero dependencies."""

    async def test_dispatch_assigns_ids(self, mock_agent):
        orch = SwarmOrchestrator(mock_agent, auto_classify=False)
        orch._execute_task = AsyncMock(return_value="done")
        tasks = [
            SwarmTask(id="", description="A", message="m"),
            SwarmTask(id="", description="B", message="m"),
        ]
        await orch.dispatch(tasks)
        # IDs should have been auto-assigned
        for task in tasks:
            assert task.id != ""

    async def test_dispatch_returns_results(self, mock_agent):
        orch = SwarmOrchestrator(mock_agent, auto_classify=False)
        orch._execute_task = AsyncMock(side_effect=lambda t: f"result_{t.id}")
        tasks = [
            SwarmTask(id="t1", description="A", message="m"),
            SwarmTask(id="t2", description="B", message="m"),
        ]
        results = await orch.dispatch(tasks)
        assert results["t1"] == "result_t1"
        assert results["t2"] == "result_t2"

    async def test_dispatch_handles_exception(self, mock_agent):
        orch = SwarmOrchestrator(mock_agent, auto_classify=False)

        async def failing_task(task):
            raise RuntimeError("boom")

        orch._execute_task = failing_task
        tasks = [SwarmTask(id="t1", description="A", message="m")]
        results = await orch.dispatch(tasks)
        assert "Error" in results["t1"]
        assert orch.tasks["t1"].status == TaskStatus.FAILED

    async def test_dispatch_respects_dependencies(self, mock_agent):
        execution_order = []
        orch = SwarmOrchestrator(mock_agent, auto_classify=False)

        async def tracking_execute(task):
            execution_order.append(task.id)
            return f"done_{task.id}"

        orch._execute_task = tracking_execute
        tasks = [
            SwarmTask(id="a", description="A", message="m"),
            SwarmTask(id="b", description="B", message="m", dependencies=["a"]),
        ]
        await orch.dispatch(tasks)
        assert execution_order.index("a") < execution_order.index("b")

    async def test_dispatch_cancelled_skips_levels(self, mock_agent):
        orch = SwarmOrchestrator(mock_agent, auto_classify=False)

        call_count = 0

        async def execute_and_cancel(task):
            nonlocal call_count
            call_count += 1
            await orch.cancel_all()
            return "done"

        orch._execute_task = execute_and_cancel
        tasks = [
            SwarmTask(id="a", description="A", message="m"),
            SwarmTask(id="b", description="B", message="m", dependencies=["a"]),
        ]
        await orch.dispatch(tasks)
        # Level 1 (task b) should not execute because we cancelled after level 0
        assert "b" not in {t.id for t in orch.tasks.values() if t.status == TaskStatus.COMPLETED}
