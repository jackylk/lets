# Conversation Layer

## 1. Why This Layer Exists

The current MVP proves that shared state works:

- humans can post work items
- agents can claim work
- agents can publish status and findings
- peer agents can read each other's activity

But this still leaves a poor human experience if the user must constantly switch
between:

- Lets web UI
- Claude Code CLI
- Codex CLI
- other agent terminals

That interaction model does not scale.

The ideal user experience is:

```text
human works primarily inside Lets
agents work primarily through Lets APIs / MCP
native CLIs remain available for deep drill-down, not as the main control plane
```

## 2. Product Insight

Lets should not be only a shared workboard.

It should become the primary collaboration surface where:

- humans talk to agents
- agents talk to humans
- agents observe shared project state
- agents coordinate with each other
- research, implementation, evidence, and decisions remain attached to the same
  conversation context

## 3. Market Signal

Several emerging products already validate the importance of a unified agent
interaction surface:

- Slock: channels and DMs where humans and agents collaborate as teammates
- Fleetify: one composer that routes prompts to Claude, Codex, Gemini, and more
- CliDeck: multiple CLI agents brought into one browser workspace
- Superconductor: multiplayer workspace for teams and coding agents

The market is converging on:

```text
one main interface for humans
many agents behind it
```

## 4. Where Lets Should Differentiate

Conversation alone is not enough.

If Lets only adds chat, it becomes another multi-agent console.

Its real differentiation is the combination of:

### 4.1 Conversation Layer

- channels
- DMs
- shared threads
- @agent mentions
- human-to-agent and agent-to-agent messaging

### 4.2 Coordination Layer

- work items
- claims
- handoffs
- agent presence
- status

### 4.3 Research Layer

- ideas
- initiatives
- hypotheses
- findings
- decisions

### 4.4 Evidence Layer

- GitHub branches
- commits
- pull requests
- benchmark results
- metrics

### 4.5 Shared State Layer

- typed collaborative objects
- branch-aware state
- promotion
- presence
- concurrent updates
- event history
- cross-device synchronization

## 5. Product Structure

```text
Lets
├── Conversation Layer
│   ├── channels
│   ├── DMs
│   ├── shared threads
│   └── @agent routing
├── Coordination Layer
│   ├── work items
│   ├── claims
│   ├── handoffs
│   └── agent status
├── Research Layer
│   ├── ideas
│   ├── initiatives
│   ├── hypotheses
│   ├── findings
│   └── decisions
└── Evidence Layer
    ├── GitHub
    ├── branches
    ├── PRs
    ├── metrics
    └── benchmarks
```

All four upper layers depend on:

```text
Shared State Layer
├── typed objects
├── branch-aware state
├── promotion
├── presence
├── event history
└── cross-device synchronization
```

## 6. UX Principle

The human should not need to ask:

- which terminal is Claude Code in
- which terminal is Codex in
- which agent currently owns the task
- where the latest finding was written

The main workspace should answer those automatically.

## 7. Ideal Interaction Pattern

### 7.1 New Idea

```text
human in #research:
  I saw this paper. Analyze whether it applies to Lets.

agent:
  I claimed the idea and started a research session.

human later:
  Show me the conclusion.

agent:
  Here are the findings, recommendation, and next step.
```

### 7.2 Work Coordination

```text
human in #lets:
  Who can take T7?

claude-code:
  I claimed T7.

codex:
  I saw T7 is already claimed. I will take T8 instead.
```

### 7.3 Human Steering

```text
human:
  Pause the current route. Prioritize deletion workflow before branch modeling.

all relevant agents:
  feedback consumed, work plan adjusted
```

## 8. Proposed Main UI

```text
┌───────────────┬──────────────────────────────┬──────────────────────┐
│ Channels      │ Conversation                  │ Context              │
│ - #project    │ human + agents                │ work item            │
│ - #research   │ shared thread                 │ findings             │
│ - #reviews    │ @claude @codex                │ agent status         │
│ - DMs         │ tool calls / responses        │ branch / metrics     │
└───────────────┴──────────────────────────────┴──────────────────────┘
```

## 9. Relationship to Native CLIs

Native CLIs still matter.

They are useful for:

- raw terminal control
- debugging
- long-running local sessions
- power-user escape hatches

But they should not be the default place where the human coordinates work.

Recommended division:

```text
Lets UI = primary collaboration surface
MCP / API = agent integration surface
Claude Code / Codex CLI = execution substrate and escape hatch
```

## 10. Implication for Roadmap

After the shared-state MVP, the next major product step should not be more schema
work alone.

It should be:

```text
Conversation MVP
```

Minimum viable conversation layer:

- one project channel
- agent messages
- human messages
- work-item-linked threads
- agent presence
- ability to trigger an agent from the Lets UI

Only after this layer exists does the product start to feel like a true workspace
rather than a side dashboard.

## 11. Summary

Lets should evolve from:

```text
shared state board for coding agents
```

to:

```text
agent-native R&D workspace where humans and agents collaborate in one place
```

The workspace should combine what current products usually split apart:

- unified conversation
- shared coordination state
- architecture exploration
- evidence-backed engineering decisions

The unifying substrate is the **Shared State Layer**. Without it, Lets is
only a better chat interface; with it, Lets becomes a durable
multi-agent collaboration system.
