# ⚡ Parallel Swarm — A0 Plugin

Run multiple Agent Zero agents at the same time. Fan out tasks, collect results, share findings between agents mid-execution.

We built this because we needed our A0 agents to research 5 markets simultaneously instead of crawling through them one by one. Turns out it's useful for a lot more than that.

## What it does

You give your agent a list of tasks. The plugin spins up parallel subordinate agents, runs them concurrently with bounded concurrency, manages token budgets so you don't blow your API bill, and collects all results back into one response.

**Key features:**

- **Parallel execution** — Up to 20 concurrent agents (default 5)
- **Task dependencies** — Build DAGs: "do A and B first, then C needs both results"
- **Token budgets** — Set total + per-task caps. No more surprise API bills.
- **Smart model routing** — Simple tasks get a cheap model, complex ones get the big guns
- **Shared memory** — Agents can pass findings to each other mid-execution via `swarm_share`
- **Adaptive throttling** — Backs off automatically when hitting rate limits

## Quick Start

### 1. Install

```bash
git clone https://github.com/up2itnow0822/a0-parallel-swarm-plugin.git
cp -r a0-parallel-swarm-plugin /path/to/agent-zero/usr/plugins/parallel_swarm
```

### 2. Enable in Settings

Agent Zero → Settings → Agent tab → Parallel Swarm → toggle on.

### 3. Use it

Your agent now has two new tools:

**`call_swarm`** — Dispatch parallel tasks:
```
Research these 3 topics simultaneously:
1. Current Bitcoin market sentiment
2. Ethereum DeFi TVL trends
3. Solana NFT marketplace activity
```

The agent will automatically use `call_swarm` to fan out the work.

**`swarm_share`** — Agents share findings with each other during execution:
```json
{
  "key": "btc_sentiment",
  "value": "Strongly bullish — 3 whale wallets accumulated 2000 BTC in 24h",
  "tags": "crypto,sentiment"
}
```

## How it works

```
You: "Research X, Y, Z simultaneously"
    │
    ▼
┌──────────────┐
│  call_swarm  │  ← Your agent dispatches tasks
└──────┬───────┘
       │
   ┌───┼───┐
   │   │   │
   ▼   ▼   ▼
  A1  A2  A3     ← Parallel subordinate agents
   │   │   │
   └───┼───┘
       │
       ▼         ← Results collected, formatted, returned
  Combined Response + Token Usage Report
```

### Task Dependencies (DAG)

```json
{
  "tasks": [
    {"id": "research", "message": "Find the top 5 competitors"},
    {"id": "pricing", "message": "Get their pricing pages"},
    {"id": "analysis", "message": "Compare and recommend", "depends_on": ["research", "pricing"]}
  ]
}
```

Level 0: `research` + `pricing` run in parallel
Level 1: `analysis` runs after both complete, with their results available

### Model Routing

When auto-classify is on, the plugin sorts tasks by complexity:

| Complexity | Routed to | Example |
|-----------|-----------|---------|
| Simple | Cheap/fast model | "Count items in this list" |
| Moderate | Default model | "Summarize this document" |
| Complex | Heavy model | "Design a system architecture" |

Configure model overrides in the settings UI to use specific models per tier.

## Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `max_concurrency` | 5 | Max parallel agents |
| `token_budget` | 100,000 | Total token cap for all tasks |
| `per_task_budget` | 20,000 | Per-task token cap |
| `auto_classify` | true | Route tasks to models by complexity |
| `shared_memory` | true | Enable `swarm_share` between agents |
| `simple_model` | (default) | Model override for simple tasks |
| `complex_model` | (default) | Model override for complex tasks |
| `backpressure_threshold` | 0.8 | Throttle when this % of slots active |

## Architecture

The plugin adds 5 modules to your A0 installation:

- `SwarmOrchestrator` — Coordinates parallel dispatch with dependency resolution
- `TokenPool` — Centralized budget management, pre-allocation prevents overruns
- `ConcurrencyManager` — Semaphore-based parallelism with adaptive backpressure
- `SwarmMemory` — Ephemeral shared key-value store for cross-agent communication
- `ModelRouter` — Classifies task complexity and routes to appropriate models

All modules are async-native and thread-safe.

## Requirements

- Agent Zero (latest version with plugin support)
- Enough API rate limit headroom for concurrent requests (check your provider)

## Built By

[AI Agent Economy](https://github.com/up2itnow0822) — Building infrastructure for autonomous AI agents.

We've been running parallel swarm execution in production for our trading research pipeline since January 2026. This plugin packages that battle-tested code for the A0 community.

## License

MIT
