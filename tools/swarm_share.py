from python.helpers.tool import Tool, Response
from plugins.parallel_swarm.python.helpers.swarm_memory import SwarmMemory


class SwarmShare(Tool):
    """Share a finding with other agents in the swarm."""

    async def execute(self, key="", value="", tags="", **kwargs):
        swarm_mem = self.agent.get_data("_swarm_memory")
        if not swarm_mem or not isinstance(swarm_mem, SwarmMemory):
            return Response(
                message="Not running in swarm mode. This tool is only available "
                "when executing as part of a swarm dispatch.",
                break_loop=False,
            )

        if not key or not value:
            return Response(
                message="Error: Both 'key' and 'value' are required.",
                break_loop=False,
            )

        tag_list = [t.strip() for t in str(tags).split(",") if t.strip()]
        await swarm_mem.share(
            agent_id=self.agent.agent_name,
            key=str(key),
            value=str(value),
            tags=tag_list,
        )
        return Response(
            message=f"Finding '{key}' shared with swarm.",
            break_loop=False,
        )
