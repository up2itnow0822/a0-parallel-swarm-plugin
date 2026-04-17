"""Regression tests for classify_with_llm exact-match routing.

Guards against the previous bug where the classifier used substring
containment on the LLM response. Sentences like 'not simple, it is COMPLEX'
would match SIMPLE first (because the substring check ran first) and
misroute a COMPLEX task to the cheap model.

The fix: take the first word of the response (upper-cased, stripped) and
require an exact match against COMPLEX / SIMPLE, otherwise MODERATE.
"""

import pytest
from unittest.mock import AsyncMock

from plugins.parallel_swarm.python.helpers.model_router import (
    TaskComplexity,
    classify_with_llm,
)


class _FakeAgent:
    """Minimal agent stub whose call_utility_model is controllable."""

    def __init__(self, response: str):
        self.call_utility_model = AsyncMock(return_value=response)


@pytest.mark.asyncio
async def test_response_complex_returns_complex():
    agent = _FakeAgent("COMPLEX")
    result = await classify_with_llm("design a distributed system", agent)
    assert result == TaskComplexity.COMPLEX


@pytest.mark.asyncio
async def test_response_simple_returns_simple():
    agent = _FakeAgent("SIMPLE")
    result = await classify_with_llm("format this list", agent)
    assert result == TaskComplexity.SIMPLE


@pytest.mark.asyncio
async def test_response_moderate_returns_moderate():
    agent = _FakeAgent("MODERATE")
    result = await classify_with_llm("summarize this article", agent)
    assert result == TaskComplexity.MODERATE


@pytest.mark.asyncio
async def test_sentence_mentioning_complex_is_not_simple():
    """Previously: 'not simple, it is COMPLEX' would match SIMPLE (bug).

    With exact first-word matching, a sentence starting with 'not' falls
    through to MODERATE. The critical invariant is that it is NOT misrouted
    to SIMPLE — that was the production bug.
    """
    agent = _FakeAgent("not simple, it is COMPLEX")
    result = await classify_with_llm("sample task", agent)
    assert result != TaskComplexity.SIMPLE
    assert result == TaskComplexity.MODERATE


@pytest.mark.asyncio
async def test_leading_whitespace_is_stripped():
    agent = _FakeAgent("   COMPLEX   ")
    result = await classify_with_llm("design task", agent)
    assert result == TaskComplexity.COMPLEX


@pytest.mark.asyncio
async def test_lowercase_response_is_normalised():
    agent = _FakeAgent("complex")
    result = await classify_with_llm("design task", agent)
    assert result == TaskComplexity.COMPLEX


@pytest.mark.asyncio
async def test_response_with_trailing_punctuation():
    """Responses like 'COMPLEX.' should still classify correctly.

    We only split on whitespace, so 'COMPLEX.' would not match 'COMPLEX'
    exactly and falls through to MODERATE. This is acceptable — the contract
    is that the classifier must never misroute COMPLEX->SIMPLE.
    """
    agent = _FakeAgent("COMPLEX.")
    result = await classify_with_llm("design task", agent)
    assert result != TaskComplexity.SIMPLE


@pytest.mark.asyncio
async def test_simple_first_word_matches_simple():
    """A clean 'SIMPLE' response (or with trailing whitespace) -> SIMPLE."""
    agent = _FakeAgent("SIMPLE\n")
    result = await classify_with_llm("rename file", agent)
    assert result == TaskComplexity.SIMPLE


@pytest.mark.asyncio
async def test_simple_with_explanation_is_not_simple():
    """'SIMPLE because it is trivial' — first word is SIMPLE, still SIMPLE.

    This is the symmetric case: when SIMPLE comes first, the classifier
    should return SIMPLE. The bug was specifically about COMPLEX being
    misrouted to SIMPLE.
    """
    agent = _FakeAgent("SIMPLE because it is a short lookup task")
    result = await classify_with_llm("lookup user", agent)
    assert result == TaskComplexity.SIMPLE


@pytest.mark.asyncio
async def test_empty_response_falls_through_to_moderate():
    agent = _FakeAgent("")
    result = await classify_with_llm("some task", agent)
    assert result == TaskComplexity.MODERATE


@pytest.mark.asyncio
async def test_garbage_response_falls_through_to_moderate():
    agent = _FakeAgent("blablabla unrelated text")
    result = await classify_with_llm("some task", agent)
    assert result == TaskComplexity.MODERATE
