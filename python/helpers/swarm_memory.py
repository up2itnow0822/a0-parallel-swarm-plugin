import asyncio
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class SwarmFinding:
    agent_id: str
    key: str
    value: str
    tags: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


class SwarmMemory:
    """In-session shared memory for parallel agents (federated learning).

    Allows agents running in parallel to share findings, avoid
    redundant work, and build on each other's results.
    This memory is ephemeral — it lives only during a swarm operation.
    """

    def __init__(self):
        self.findings: dict[str, SwarmFinding] = {}
        self._lock = asyncio.Lock()

    async def share(self, agent_id: str, key: str, value: str, tags: list[str] | None = None):
        """Agent shares a finding with the swarm."""
        async with self._lock:
            self.findings[key] = SwarmFinding(
                agent_id=agent_id,
                key=key,
                value=value,
                tags=tags or [],
                timestamp=datetime.now(),
            )

    async def get(self, key: str) -> SwarmFinding | None:
        """Get a specific finding by key."""
        async with self._lock:
            return self.findings.get(key)

    async def query(self, tags: list[str] | None = None, keyword: str | None = None) -> list[SwarmFinding]:
        """Query shared findings by tags or keyword."""
        async with self._lock:
            results = list(self.findings.values())

            if tags:
                tag_set = set(tags)
                results = [f for f in results if tag_set & set(f.tags)]

            if keyword:
                kw_lower = keyword.lower()
                results = [
                    f for f in results
                    if kw_lower in f.key.lower() or kw_lower in f.value.lower()
                ]

            return results

    async def get_all(self) -> list[SwarmFinding]:
        """Get all findings."""
        async with self._lock:
            return list(self.findings.values())

    async def get_summary(self) -> str:
        """Get human-readable summary of all shared findings."""
        async with self._lock:
            if not self.findings:
                return ""

            lines = []
            for finding in self.findings.values():
                tags_str = f" [{', '.join(finding.tags)}]" if finding.tags else ""
                lines.append(
                    f"- **{finding.key}** (from {finding.agent_id}){tags_str}: {finding.value}"
                )
            return "\n".join(lines)

    async def clear(self):
        """Clear all findings."""
        async with self._lock:
            self.findings.clear()

    async def count(self) -> int:
        """Number of findings stored."""
        async with self._lock:
            return len(self.findings)
