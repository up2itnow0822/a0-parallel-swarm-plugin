"""
Plugin lifecycle hooks for the parallel_swarm plugin.

Agent Zero calls install() when the plugin is enabled and
uninstall() when it is disabled or removed.
"""


def install():
    print("Parallel Swarm plugin installed")


def uninstall():
    print("Parallel Swarm plugin uninstalled")
