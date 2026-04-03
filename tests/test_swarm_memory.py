"""Tests for SwarmMemory — store/retrieve, federation, querying."""

import pytest
from plugins.parallel_swarm.python.helpers.swarm_memory import SwarmMemory


class TestSwarmMemoryBasic:
    async def test_share_and_get(self, swarm_memory):
        await swarm_memory.share("agent1", "key1", "value1")
        finding = await swarm_memory.get("key1")
        assert finding is not None
        assert finding.agent_id == "agent1"
        assert finding.key == "key1"
        assert finding.value == "value1"

    async def test_get_nonexistent_key(self, swarm_memory):
        finding = await swarm_memory.get("nope")
        assert finding is None

    async def test_share_overwrites_same_key(self, swarm_memory):
        await swarm_memory.share("a1", "key", "old")
        await swarm_memory.share("a2", "key", "new")
        finding = await swarm_memory.get("key")
        assert finding.value == "new"
        assert finding.agent_id == "a2"

    async def test_count(self, swarm_memory):
        assert await swarm_memory.count() == 0
        await swarm_memory.share("a1", "k1", "v1")
        await swarm_memory.share("a1", "k2", "v2")
        assert await swarm_memory.count() == 2

    async def test_get_all(self, swarm_memory):
        await swarm_memory.share("a1", "k1", "v1")
        await swarm_memory.share("a2", "k2", "v2")
        all_findings = await swarm_memory.get_all()
        assert len(all_findings) == 2
        keys = {f.key for f in all_findings}
        assert keys == {"k1", "k2"}

    async def test_clear(self, swarm_memory):
        await swarm_memory.share("a1", "k1", "v1")
        await swarm_memory.clear()
        assert await swarm_memory.count() == 0


class TestSwarmMemoryQuery:
    async def test_query_by_tags(self, swarm_memory):
        await swarm_memory.share("a1", "btc", "bullish", tags=["crypto", "sentiment"])
        await swarm_memory.share("a1", "weather", "sunny", tags=["misc"])
        results = await swarm_memory.query(tags=["crypto"])
        assert len(results) == 1
        assert results[0].key == "btc"

    async def test_query_by_keyword_in_value(self, swarm_memory):
        await swarm_memory.share("a1", "k1", "Bitcoin is bullish")
        await swarm_memory.share("a1", "k2", "Ethereum is bearish")
        results = await swarm_memory.query(keyword="bitcoin")
        assert len(results) == 1
        assert results[0].key == "k1"

    async def test_query_by_keyword_in_key(self, swarm_memory):
        await swarm_memory.share("a1", "btc_price", "50000")
        await swarm_memory.share("a1", "eth_price", "3000")
        results = await swarm_memory.query(keyword="btc")
        assert len(results) == 1

    async def test_query_combined_tags_and_keyword(self, swarm_memory):
        await swarm_memory.share("a1", "k1", "Bitcoin bullish", tags=["crypto"])
        await swarm_memory.share("a1", "k2", "Bitcoin ETF", tags=["finance"])
        await swarm_memory.share("a1", "k3", "sunny day", tags=["crypto"])
        # Tags filter to k1, k3; keyword "bitcoin" filters to k1
        results = await swarm_memory.query(tags=["crypto"], keyword="bitcoin")
        assert len(results) == 1
        assert results[0].key == "k1"

    async def test_query_no_match(self, swarm_memory):
        await swarm_memory.share("a1", "k1", "v1", tags=["a"])
        results = await swarm_memory.query(tags=["z"])
        assert len(results) == 0


class TestSwarmMemorySummary:
    async def test_summary_empty(self, swarm_memory):
        summary = await swarm_memory.get_summary()
        assert summary == ""

    async def test_summary_includes_findings(self, swarm_memory):
        await swarm_memory.share("a1", "finding1", "result1", tags=["tag1"])
        summary = await swarm_memory.get_summary()
        assert "finding1" in summary
        assert "result1" in summary
        assert "a1" in summary
        assert "tag1" in summary


class TestSwarmMemoryFederation:
    """Test that multiple agents can share and read each other's findings."""

    async def test_cross_agent_visibility(self, swarm_memory):
        await swarm_memory.share("agent_1", "market_data", "BTC at 60k")
        await swarm_memory.share("agent_2", "sentiment", "bullish")
        # Agent 3 can read both
        all_findings = await swarm_memory.get_all()
        assert len(all_findings) == 2
        agents = {f.agent_id for f in all_findings}
        assert agents == {"agent_1", "agent_2"}

    async def test_concurrent_writes(self, swarm_memory):
        """Simulate concurrent agent writes."""
        import asyncio

        async def write(agent_id, key, value):
            await swarm_memory.share(agent_id, key, value)

        tasks = [
            write(f"agent_{i}", f"key_{i}", f"value_{i}")
            for i in range(10)
        ]
        await asyncio.gather(*tasks)
        assert await swarm_memory.count() == 10
