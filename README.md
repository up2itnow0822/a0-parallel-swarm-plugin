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

## Example: Research 5 Markets Simultaneously

Here's a concrete example dispatching 5 parallel market research tasks with a dependency chain — the final synthesis task waits for all research to complete:

```json
{
  "tasks": [
    {
      "id": "crypto",
      "description": "Analyze cryptocurrency market",
      "message": "Research current BTC and ETH price action, volume trends, and whale activity. Provide a 2-paragraph summary with key data points.",
      "complexity": "moderate",
      "priority": 0
    },
    {
      "id": "equities",
      "description": "Analyze US equities market",
      "message": "Research S&P 500, NASDAQ, and Dow performance over the past week. Note any sector rotation or unusual volume.",
      "complexity": "moderate",
      "priority": 0
    },
    {
      "id": "forex",
      "description": "Analyze forex market",
      "message": "Research USD strength index, EUR/USD, and GBP/USD trends. Note central bank policy impacts.",
      "complexity": "simple",
      "priority": 0
    },
    {
      "id": "commodities",
      "description": "Analyze commodities market",
      "message": "Research gold, oil, and natural gas price movements. Note supply/demand factors driving changes.",
      "complexity": "simple",
      "priority": 0
    },
    {
      "id": "defi",
      "description": "Analyze DeFi ecosystem",
      "message": "Research total DeFi TVL, top protocol inflows/outflows, and emerging yield opportunities.",
      "complexity": "moderate",
      "priority": 0
    },
    {
      "id": "synthesis",
      "description": "Cross-market synthesis and recommendations",
      "message": "Using findings from all 5 market analyses, identify cross-market correlations, risk factors, and provide 3 actionable trading recommendations with confidence levels.",
      "complexity": "complex",
      "priority": 1,
      "depends_on": ["crypto", "equities", "forex", "commodities", "defi"]
    }
  ],
  "max_concurrency": 5,
  "token_budget": 150000
}
```

**Execution flow:**

```
Level 0 (parallel): crypto + equities + forex + commodities + defi
                     ↓           ↓         ↓          ↓          ↓
                     └───────────┴─────────┴──────────┴──────────┘
                                           ↓
Level 1 (sequential):              synthesis (uses all results)
```

**Expected output format:**

```
## Task: Analyze cryptocurrency market
**Status:** completed

BTC trading at $61,200 with 24h volume up 15%...

---

## Task: Analyze US equities market
**Status:** completed

S&P 500 closed at 5,180, up 0.8% on the week...

---

... (3 more market tasks) ...

---

## Task: Cross-market synthesis and recommendations
**Status:** completed

**Cross-Market Correlations:**
1. Risk-on sentiment across crypto and equities...

**Recommendations:**
1. Long BTC/USD (confidence: 72%) — whale accumulation + positive equity correlation
2. Short EUR/USD (confidence: 65%) — ECB dovish signals vs Fed hold
3. Long Gold (confidence: 58%) — geopolitical hedge with declining real yields

---
**Swarm Summary:** 6/6 tasks completed | Total tokens consumed: 47,832
```

## Requirements

- Agent Zero (latest version with plugin support)
- Enough API rate limit headroom for concurrent requests (check your provider)

## Built By

[AI Agent Economy](https://github.com/up2itnow0822) — Building infrastructure for autonomous AI agents.

We've been running parallel swarm execution in production for our trading research pipeline since January 2026. This plugin packages that battle-tested code for the A0 community.

## License

MIT
