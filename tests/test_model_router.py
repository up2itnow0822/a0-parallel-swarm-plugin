"""Tests for ModelRouter — complexity classification, model assignment."""

import pytest
from unittest.mock import AsyncMock
from plugins.parallel_swarm.python.helpers.model_router import (
    TaskComplexity,
    classify_heuristic,
    classify_with_llm,
    classify_complexity,
    select_model_config,
)


class TestHeuristicClassification:
    def test_simple_keyword(self):
        assert classify_heuristic("format this list") == TaskComplexity.SIMPLE

    def test_complex_keyword(self):
        assert classify_heuristic("architect a distributed system") == TaskComplexity.COMPLEX

    def test_short_description_is_simple(self):
        assert classify_heuristic("hello") == TaskComplexity.SIMPLE

    def test_long_description_is_complex(self):
        desc = "x " * 300  # 600 chars
        assert classify_heuristic(desc) == TaskComplexity.COMPLEX

    def test_moderate_length_is_moderate(self):
        desc = "Analyze the quarterly earnings report and provide key insights for investment decisions based on year over year growth metrics and margin analysis"
        # >100 chars, <500 chars, no strong keywords
        assert len(desc) > 100
        assert len(desc) < 500
        assert classify_heuristic(desc) == TaskComplexity.MODERATE

    def test_complex_keywords_take_priority(self):
        # Even short, "security audit" triggers COMPLEX
        assert classify_heuristic("security audit") == TaskComplexity.COMPLEX

    def test_translate_is_simple(self):
        assert classify_heuristic("translate this to Spanish") == TaskComplexity.SIMPLE

    def test_refactor_is_complex(self):
        assert classify_heuristic("refactor the authentication module") == TaskComplexity.COMPLEX

    def test_case_insensitive(self):
        assert classify_heuristic("FORMAT this data") == TaskComplexity.SIMPLE
        assert classify_heuristic("ARCHITECT a new service") == TaskComplexity.COMPLEX


class TestLLMClassification:
    async def test_llm_returns_simple(self, mock_agent):
        mock_agent.call_utility_model = AsyncMock(return_value="SIMPLE")
        result = await classify_with_llm("some task", mock_agent)
        assert result == TaskComplexity.SIMPLE

    async def test_llm_returns_complex(self, mock_agent):
        mock_agent.call_utility_model = AsyncMock(return_value="COMPLEX")
        result = await classify_with_llm("some task", mock_agent)
        assert result == TaskComplexity.COMPLEX

    async def test_llm_returns_moderate_on_unknown(self, mock_agent):
        mock_agent.call_utility_model = AsyncMock(return_value="BANANA")
        result = await classify_with_llm("some task", mock_agent)
        assert result == TaskComplexity.MODERATE

    async def test_llm_fallback_on_error(self, mock_agent):
        mock_agent.call_utility_model = AsyncMock(side_effect=Exception("API error"))
        result = await classify_with_llm("format this list", mock_agent)
        # Falls back to heuristic — "format" keyword → SIMPLE
        assert result == TaskComplexity.SIMPLE


class TestClassifyComplexity:
    async def test_with_llm_enabled(self, mock_agent):
        mock_agent.call_utility_model = AsyncMock(return_value="COMPLEX")
        result = await classify_complexity("task", mock_agent, use_llm=True)
        assert result == TaskComplexity.COMPLEX

    async def test_with_llm_disabled(self, mock_agent):
        result = await classify_complexity("format data", mock_agent, use_llm=False)
        assert result == TaskComplexity.SIMPLE


class TestModelSelection:
    def test_simple_task_gets_simple_model(self):
        from agent import AgentConfig
        config = AgentConfig()
        new_config = select_model_config(TaskComplexity.SIMPLE, config)
        assert new_config.chat_model == "gpt-4o-mini"

    def test_complex_task_gets_complex_model(self):
        from agent import AgentConfig
        config = AgentConfig()
        new_config = select_model_config(TaskComplexity.COMPLEX, config)
        assert new_config.chat_model == "gpt-4o"

    def test_moderate_task_keeps_default(self):
        from agent import AgentConfig
        config = AgentConfig()
        original_model = config.chat_model
        new_config = select_model_config(TaskComplexity.MODERATE, config)
        assert new_config.chat_model == original_model

    def test_no_simple_override_keeps_default(self):
        from agent import AgentConfig
        config = AgentConfig()
        config.swarm_model_simple = None
        new_config = select_model_config(TaskComplexity.SIMPLE, config)
        assert new_config.chat_model == config.chat_model

    def test_no_complex_override_keeps_default(self):
        from agent import AgentConfig
        config = AgentConfig()
        config.swarm_model_complex = None
        new_config = select_model_config(TaskComplexity.COMPLEX, config)
        assert new_config.chat_model == config.chat_model
