"""
Agent Zero agent_init hook for the parallel_swarm plugin.

Called by Agent Zero when initializing an agent config. Sets up swarm-specific
config attributes with sensible defaults sourced from the plugin's default_config.yaml.
"""


def agent_init(agent, config):
    """Register swarm configuration attributes on the agent config.

    This ensures that config.swarm_enabled, config.swarm_max_concurrency, etc.
    are always available, even if not explicitly set in the project config.
    """
    # Guard: only add attributes that don't already exist (respect explicit overrides)
    if not hasattr(config, "swarm_enabled"):
        config.swarm_enabled = True

    if not hasattr(config, "swarm_max_concurrency"):
        config.swarm_max_concurrency = 5

    if not hasattr(config, "swarm_token_budget"):
        config.swarm_token_budget = 100000

    if not hasattr(config, "swarm_per_task_budget"):
        config.swarm_per_task_budget = 20000

    if not hasattr(config, "swarm_auto_classify"):
        config.swarm_auto_classify = True

    if not hasattr(config, "swarm_model_simple"):
        config.swarm_model_simple = ""

    if not hasattr(config, "swarm_model_complex"):
        config.swarm_model_complex = ""

    if not hasattr(config, "swarm_backpressure_threshold"):
        config.swarm_backpressure_threshold = 0.8

    if not hasattr(config, "swarm_shared_memory"):
        config.swarm_shared_memory = True
