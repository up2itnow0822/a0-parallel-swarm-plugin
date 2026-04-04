"""Shared fixtures for parallel swarm plugin tests.

Mocks Agent Zero's runtime classes so tests run standalone without
a live A0 instance. All mocks reflect A0's actual interface as of
the latest commit (2026-04).
"""

import sys
import types
import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

# Resolve repo root dynamically so tests work from any working directory
_REPO_ROOT = Path(__file__).parent.parent.resolve()
_PYTHON_DIR = _REPO_ROOT / "python"

import pytest


# ---------------------------------------------------------------------------
# Stub modules that the plugin imports from Agent Zero at runtime
# ---------------------------------------------------------------------------

def _install_a0_stubs():
    """Create fake top-level modules so plugin imports resolve."""

    # --- helpers.print_style ---
    print_style_mod = types.ModuleType("helpers.print_style")

    class _PrintStyle:
        def __init__(self, **kw):
            pass
        def print(self, *a, **kw):
            pass
        def stream(self, *a, **kw):
            pass

    print_style_mod.PrintStyle = _PrintStyle
    sys.modules.setdefault("helpers", types.ModuleType("helpers"))
    sys.modules["helpers.print_style"] = print_style_mod

    # --- helpers.tool ---
    tool_mod = types.ModuleType("helpers.tool")

    @dataclass
    class Response:
        message: str
        break_loop: bool
        additional: dict[str, Any] | None = None

    class Tool:
        def __init__(self, agent=None, name="", method=None, args=None, message="", loop_data=None, **kw):
            self.agent = agent
            self.name = name
            self.method = method
            self.args = args or {}
            self.loop_data = loop_data
            self.message = message

        async def execute(self, **kw):
            raise NotImplementedError

        def get_log_object(self):
            return MagicMock()

    tool_mod.Tool = Tool
    tool_mod.Response = Response
    sys.modules["helpers.tool"] = tool_mod

    # --- helpers.dirty_json ---
    dirty_json_mod = types.ModuleType("helpers.dirty_json")

    class _DirtyJson:
        @staticmethod
        def parse_string(s):
            import json
            return json.loads(s)

    dirty_json_mod.DirtyJson = _DirtyJson
    sys.modules["helpers.dirty_json"] = dirty_json_mod
    sys.modules.setdefault("helpers", types.ModuleType("helpers"))
    # Make helpers a proper package with submodules accessible
    helpers_pkg = sys.modules["helpers"]
    helpers_pkg.dirty_json = dirty_json_mod
    helpers_pkg.print_style = print_style_mod
    helpers_pkg.tool = tool_mod

    # --- helpers.extension ---
    ext_mod = types.ModuleType("helpers.extension")
    ext_mod.call_extensions_async = AsyncMock()
    sys.modules["helpers.extension"] = ext_mod
    helpers_pkg.extension = ext_mod

    # --- helpers.strings ---
    strings_mod = types.ModuleType("helpers.strings")
    strings_mod.sanitize_string = lambda s: s
    sys.modules["helpers.strings"] = strings_mod
    helpers_pkg.strings = strings_mod

    # --- agent module ---
    agent_mod = types.ModuleType("agent")

    @dataclass
    class UserMessage:
        message: str = ""
        attachments: list = field(default_factory=list)

    class LoopData:
        pass

    class AgentConfig:
        def __init__(self):
            self.chat_model = "gpt-4o"
            self.swarm_enabled = True
            self.swarm_max_concurrency = 5
            self.swarm_token_budget = 100000
            self.swarm_per_task_budget = 20000
            self.swarm_auto_classify = True
            self.swarm_model_simple = "gpt-4o-mini"
            self.swarm_model_complex = "gpt-4o"
            self.profile = ""

    class AgentContext:
        def __init__(self):
            self.log = MagicMock()

    class Agent:
        DATA_NAME_SUPERIOR = "_superior"
        DATA_NAME_SUBORDINATE = "_subordinate"
        DATA_NAME_CTX_WINDOW = "ctx_window"
        DATA_NAME_SWARM_ORCHESTRATOR = "_swarm_orchestrator"

        def __init__(self, number=0, config=None, context=None):
            self.number = number
            self.config = config or AgentConfig()
            self.context = context or AgentContext()
            self.data = {}
            self.agent_name = f"Agent {number}"
            self.history = MagicMock()

        def set_data(self, key, value):
            self.data[key] = value

        def get_data(self, key):
            return self.data.get(key)

        def hist_add_user_message(self, msg):
            pass

        def hist_add_tool_result(self, *a, **kw):
            pass

        async def monologue(self):
            return "Mock monologue result"

        async def call_extensions(self, name, **kw):
            pass

        async def call_utility_model(self, system="", message="", background=False):
            return "MODERATE"

    agent_mod.Agent = Agent
    agent_mod.AgentConfig = AgentConfig
    agent_mod.AgentContext = AgentContext
    agent_mod.UserMessage = UserMessage
    agent_mod.LoopData = LoopData
    sys.modules["agent"] = agent_mod

    # --- initialize module ---
    init_mod = types.ModuleType("initialize")
    init_mod.initialize_agent = lambda: AgentConfig()
    sys.modules["initialize"] = init_mod

    # --- Plugin path aliases (the plugin imports from plugins.parallel_swarm.python.helpers.*) ---
    # We make those resolve to the actual files by adding the repo root's parent to sys.path
    # under the name "plugins.parallel_swarm"
    plugins_pkg = types.ModuleType("plugins")
    plugins_pkg.__path__ = []
    sys.modules.setdefault("plugins", plugins_pkg)

    ps_pkg = types.ModuleType("plugins.parallel_swarm")
    ps_pkg.__path__ = [str(_REPO_ROOT)]
    sys.modules["plugins.parallel_swarm"] = ps_pkg

    ps_python = types.ModuleType("plugins.parallel_swarm.python")
    ps_python.__path__ = [str(_REPO_ROOT / "python")]
    sys.modules["plugins.parallel_swarm.python"] = ps_python

    ps_helpers = types.ModuleType("plugins.parallel_swarm.python.helpers")
    ps_helpers.__path__ = [str(_REPO_ROOT / "python" / "helpers")]
    sys.modules["plugins.parallel_swarm.python.helpers"] = ps_helpers


# Install stubs before any test imports
_install_a0_stubs()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_agent():
    """Return a mock Agent instance with standard config."""
    from agent import Agent, AgentConfig, AgentContext
    config = AgentConfig()
    ctx = AgentContext()
    agent = Agent(number=0, config=config, context=ctx)
    return agent


@pytest.fixture
def token_pool():
    """Return a fresh TokenPool."""
    from plugins.parallel_swarm.python.helpers.token_pool import TokenPool
    return TokenPool(total_budget=100000, per_task_default=20000)


@pytest.fixture
def concurrency_manager():
    """Return a fresh ConcurrencyManager."""
    from plugins.parallel_swarm.python.helpers.concurrency import ConcurrencyManager
    return ConcurrencyManager(max_concurrency=3)


@pytest.fixture
def swarm_memory():
    """Return a fresh SwarmMemory."""
    from plugins.parallel_swarm.python.helpers.swarm_memory import SwarmMemory
    return SwarmMemory()
