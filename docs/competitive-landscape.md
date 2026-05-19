# Competitive Landscape

## 1. Summary

The market is converging on a clear need:

```text
humans need one main workspace
multiple coding agents run behind it
```

But current products usually solve only part of the problem.

## 2. Product Categories

### 2.1 Mature Team Workspaces

#### Superconductor

Strengths:

- team-oriented product
- GitHub integration
- tickets
- parallel implementations
- live previews
- guided review
- mobile support
- support for multiple coding agents

Assessment:

- most mature end-to-end product observed
- strongest reference for how a polished team product should feel
- more cloud workspace than local-agent shared-state system

### 2.2 Unified Conversation / Command Centers

#### Slock

Strengths:

- channels
- DMs
- humans and agents collaborate in one conversation space
- local daemon
- persistent memory

Assessment:

- closest visible reference for the ideal Lets interaction model
- less evidence yet of deeper software R&D workflows

#### Fleetify

Strengths:

- one composer
- `@claude`, `@codex`, `@gemini`
- unified thread
- worktree isolation
- sandboxing and spend tracking

Assessment:

- very strong command-center direction
- appears close to the future Lets main interaction surface

### 2.3 Local Multi-Agent Consoles

#### CliDeck

Strengths:

- one browser tab for multiple local CLI agents
- session resume
- working / idle status
- project grouping
- roles
- search
- lightweight autopilot routing

Assessment:

- likely the most practical answer to the immediate pain of juggling terminals
- mature local UX reference
- still a session aggregator more than a shared R&D workspace

### 2.4 Shared Memory / Shared State Products

#### memctl

Strengths:

- branch-aware memory
- MCP
- cross-device sync
- project / branch scopes

#### NeverZero

Strengths:

- live shared runtime state
- rooms
- claims
- handoffs
- packets
- audit trails

#### Engram

Strengths:

- shared memory across agents and tools

Assessment:

- these products validate the shared-state thesis
- they do not appear to provide a full human-facing R&D workspace

## 3. Relative Evaluation

| Capability | Superconductor | Slock | Fleetify | CliDeck | Lets Goal |
|---|---:|---:|---:|---:|---:|
| Unified human interface | strong | strong | strong | medium | strong |
| Local agents | medium | strong | medium | strong | strong |
| Team collaboration | strong | medium | medium | weak | strong |
| GitHub workflow | strong | unclear | medium | weak | strong |
| Shared state | medium | medium | medium | weak | strong |
| Research / hypothesis graph | weak | weak | weak | weak | strong |
| Benchmark-linked decisions | weak | weak | weak | weak | strong |
| Conversation-first UX | medium | strong | strong | medium | strong |

## 4. Best-in-Class by Question

### Best overall maturity

`Superconductor`

### Best match for unified conversation

`Slock`

### Best local multi-agent console

`CliDeck`

### Best command-center direction

`Fleetify`

## 5. What Lets Should Learn

### From Superconductor

- make the product complete, not just clever
- GitHub, review, preview, and team workflow matter

### From Slock

- channels and DMs are the right mental model for unified interaction
- agents should feel like teammates, not subcommands

### From Fleetify

- one composer with `@agent` routing is powerful
- attribution and inspectable outputs matter

### From CliDeck

- solve the immediate context-switching pain first
- local agents need a practical daily driver

## 6. Lets Differentiation

Lets should not compete as:

- another terminal grid
- another agent launcher
- another generic shared-memory store

It should occupy the intersection of:

```text
unified conversation
+ team collaboration
+ shared state
+ research / hypothesis management
+ evidence-aware engineering
```

## 7. Strategic Position

The intended product is:

```text
Agent-native R&D workspace for teams
```

The underlying technical system is:

```text
Shared State Layer backed by DBay
```

The strongest visible whitespace in the market is:

- conversation-first interaction
- plus branch-aware shared state
- plus architecture / evidence graph
- plus GitHub convergence

## 8. Current Conclusion

No observed product fully covers the exact Lets vision.

The closest pieces are distributed across multiple companies:

- Slock for unified conversation
- Superconductor for mature team workflow
- CliDeck for local daily usability
- memctl / NeverZero for shared-state direction

That combination is exactly where Lets can be differentiated.

