from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent import Agent, AgentConfig


class TaskComplexity(Enum):
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"


# Heuristic keywords for fast classification without LLM
_COMPLEX_KEYWORDS = [
    "architect", "design", "refactor", "debug complex", "optimize",
    "cross-domain", "integrate multiple", "security audit", "performance",
    "distributed", "concurrent", "migration", "system design",
]

_SIMPLE_KEYWORDS = [
    "format", "list", "count", "lookup", "translate", "summarize briefly",
    "extract", "convert", "rename", "simple", "trivial", "basic",
]


CLASSIFY_PROMPT = """Classify this task's complexity as exactly one of: SIMPLE, MODERATE, COMPLEX

SIMPLE: Factual lookup, formatting, translation, simple data extraction, short summaries
MODERATE: Code generation, multi-step analysis, document summarization, data transformation
COMPLEX: Architecture design, creative writing, cross-domain synthesis, debugging complex systems, long-context reasoning

Task: {task_description}

Respond with only the classification word."""


def classify_heuristic(task_description: str) -> TaskComplexity:
    """Fast heuristic classification based on keywords."""
    desc_lower = task_description.lower()
    length = len(task_description)

    # Check complex keywords first
    for kw in _COMPLEX_KEYWORDS:
        if kw in desc_lower:
            return TaskComplexity.COMPLEX

    # Check simple keywords
    for kw in _SIMPLE_KEYWORDS:
        if kw in desc_lower:
            return TaskComplexity.SIMPLE

    # Length-based heuristic
    if length < 100:
        return TaskComplexity.SIMPLE
    elif length > 500:
        return TaskComplexity.COMPLEX

    return TaskComplexity.MODERATE


async def classify_with_llm(task_description: str, agent: "Agent") -> TaskComplexity:
    """Use the utility model to classify task complexity."""
    try:
        response = await agent.call_utility_model(
            system="You are a task complexity classifier. Respond with exactly one word.",
            message=CLASSIFY_PROMPT.format(task_description=task_description),
            background=True,
        )
        response_up = response.strip().upper()
        first_word = response_up.split()[0] if response_up else ""
        if first_word == "COMPLEX":
            return TaskComplexity.COMPLEX
        elif first_word == "SIMPLE":
            return TaskComplexity.SIMPLE
        else:
            return TaskComplexity.MODERATE
    except Exception:
        # Fallback to heuristic on any error
        return classify_heuristic(task_description)


async def classify_complexity(
    task_description: str, agent: "Agent", use_llm: bool = True
) -> TaskComplexity:
    """Classify task complexity. Uses LLM if enabled, falls back to heuristic."""
    if use_llm:
        return await classify_with_llm(task_description, agent)
    return classify_heuristic(task_description)


def select_model_config(
    complexity: TaskComplexity, config: "AgentConfig"
) -> "AgentConfig":
    """Select the appropriate AgentConfig based on task complexity.

    Returns a copy of the config with the model swapped for the task tier.
    If no tier-specific model is configured, returns the original config.
    """
    import copy

    if complexity == TaskComplexity.SIMPLE and config.swarm_model_simple:
        new_config = copy.copy(config)
        new_config.chat_model = config.swarm_model_simple
        return new_config
    elif complexity == TaskComplexity.COMPLEX and config.swarm_model_complex:
        new_config = copy.copy(config)
        new_config.chat_model = config.swarm_model_complex
        return new_config

    # MODERATE or no override — use default chat model
    return config
