# Multi-Agent Collaboration Workspace Architecture

## 1. Purpose

This system is a collaboration workspace for multiple humans and multiple local
coding agents jointly researching and developing the same software project.

It is intended for situations like:

- one developer running several agents locally, such as Claude Code and Codex
- several teammates each running their own local coding agents
- a project that contains both ordinary engineering work and exploratory work
  across multiple competing architecture paths
- a human lead who wants to preserve control over goals, trade-offs, and final
  decisions while letting agents perform much of the research and execution

The system is not a replacement for GitHub. GitHub remains the source of truth
for code review, merge, and CI. The collaboration workspace adds the parts that
GitHub does not model well:

- goals and priorities
- exploratory architecture paths
- ideas entering from papers, blogs, repos, and benchmark anomalies
- agent state and handoff
- branch-local findings
- evidence and benchmark history
- human feedback and formal decisions

The deeper technical thesis is that this is not merely an "agent memory"
problem. It is a **multi-agent shared state coordination** problem.

### 1.1 System Layers

```text
Experience Layer
├── Conversation
├── Blackboard
├── Architecture Graph
├── Workboard
└── Metrics UI

Domain Layer
├── Coordination
├── Research
└── Evidence

Shared State Layer
├── typed objects
├── branch-aware state
├── promotion
├── presence
├── claims
├── findings
├── feedback
├── decisions
└── event history

Integration Layer
├── MCP
├── Local Client
├── GitHub
└── benchmark runners
```

The `Shared State Layer` is an Lets system concept. `DBay` is the backing
implementation for that layer.

## 2. Product Goals

The workspace should let humans:

1. Publish goals, priorities, ideas, feedback, and decisions in one place.
2. See what architecture paths are currently being explored.
3. See what each agent is doing, on which branch, and with what latest result.
4. Inspect evidence such as LoCoMo and PersonaMem scores by branch and commit.
5. Add a new idea from an external source and let an agent claim and research it.
6. Decide whether an idea should be rejected, attached to an existing path, or
   promoted into a formal initiative.
7. Onboard a new teammate or new agent without manually reconstructing all
   project context.

The workspace should let agents:

1. Discover active goals, initiatives, and open ideas at session start.
2. Learn what peer agents are already doing before starting work.
3. Search and reuse branch-local findings, artifacts, and benchmark results.
4. Claim ideas or tasks to avoid duplicated effort.
5. Report progress, publish findings, and request human decisions.
6. Work on separate exploratory branches without polluting global project truth.

## 3. Core Design Principle

The system should be organized around:

```text
goal -> track -> initiative -> hypothesis -> branch -> task -> artifact -> evidence -> decision
```

Tasks matter, but they are not the top-level organizing unit. In exploratory
engineering, the most important object is the **hypothesis** being tested and
the evidence that supports or refutes it.

## 4. System Boundary

### 4.1 GitHub

GitHub is the source of truth for:

- repository
- commit
- Git branch
- pull request
- review
- merge
- CI status

The collaboration workspace should read from GitHub and attach higher-level
meaning to GitHub objects, but it should not reimplement source control or PR
merging.

### 4.2 DBay

DBay is the source of truth for collaboration state:

- goals
- tracks
- ideas
- initiatives
- hypotheses
- agent sessions
- work status
- findings
- feedback
- decisions
- artifact metadata
- benchmark metadata
- event log

DBay is also where **state branches** live.

More precisely:

```text
Shared State Layer = Lets system capability
DBay Collaboration Store = backing implementation
```

### 4.3 Object Storage / File Storage

Large payloads should not live directly in collaboration state:

- raw benchmark outputs
- logs
- screenshots
- reports
- datasets
- generated design files

DBay stores metadata and references; object storage or normal file storage keeps
the payload.

### 4.4 Web Collaboration Console

The web console is the human control surface:

- conversation surface
- blackboard
- architecture graph
- idea inbox
- agent workboard
- metrics and evidence
- decisions needing review

### 4.5 Local Collaboration Client

Each laptop installs a local client that contains:

- MCP server for coding agents
- local daemon
- Git scanner
- benchmark/test runner scanner
- offline cache
- CLI for humans and scripts

This is the standard edge connector for Claude Code, Codex, and future agents.

## 5. Why DBay Branches Are Needed

Yes, this architecture should use DBay's branch capability.

The reason is that Git branches alone are insufficient.

A Git branch stores code history. It does not naturally store:

- a branch-local hypothesis
- agent reasoning about why a route is promising
- local benchmark results before a decision is made
- rejected sub-ideas inside a larger route
- branch-specific working assumptions
- branch-local handoff notes

If all of that is written directly into one global state, exploratory work from
multiple agents will pollute each other and make the global project state noisy.

Therefore the system needs **state branches** in DBay in addition to Git
branches in GitHub.

## 6. State Branch Model

### 6.1 Branch Types

#### `project-main`

Global accepted state:

- approved goals
- current roadmap
- adopted architecture
- accepted conventions
- authoritative baseline metrics
- finalized decisions

#### `track-*`

Long-lived state for a strategic track:

- track goals
- track-specific background knowledge
- initiative history
- decisions specific to that track

Example:

```text
track-b-recall-quality
```

#### `initiative-*`

Exploratory state for one architecture route:

- hypotheses
- design evolution
- findings
- local experiments
- artifacts
- associated Git branches
- open questions

Example:

```text
initiative-topic-indexed-working-memory
```

#### `session-*`

Ephemeral state for one agent work session:

- temporary notes
- in-progress findings
- draft comparison
- current blockers
- handoff material

Example:

```text
session-codex-jacky-mbp-2026-05-18T10-30
```

### 6.2 Promotion Flow

Knowledge should move upward only after validation:

```text
session finding
  -> initiative accepted finding
    -> track convention or conclusion
      -> project-main accepted decision
```

This allows many agents to explore independently without every intermediate
thought entering the global truth set.

### 6.3 Relation to Git Branches

A DBay state branch and a Git branch are related but not identical.

Recommended relationship:

```text
initiative
  -> one DBay initiative branch
  -> zero or more Git branches
```

Examples:

- An idea can be researched on a DBay branch before any code exists.
- One initiative can have multiple Git branches for competing prototypes.
- A Git branch may be short-lived, while the initiative state branch persists
  across several implementation attempts.

The system should explicitly store links such as:

```text
state_branch_id
git_repo
git_branch_ref
pull_request_ref
initiative_id
```

## 7. Core Domain Model

### 7.1 Strategic Objects

#### `Project`

Top-level collaboration unit.

#### `Goal`

A desired project or track outcome.

Examples:

- LoCoMo overall >= 80%
- PersonaMem preference questions >= 55%

#### `Track`

A stable long-running workstream.

Examples:

- Recall quality
- Cost reduction
- Dashboard

#### `Initiative`

A chosen architecture path worth active investment.

Examples:

- conditional profile inject
- topic-indexed working memory
- agentic walk

### 7.2 Intake Objects

#### `Signal`

An external or internal input:

- article
- paper
- blog
- repo
- benchmark anomaly
- user feedback

#### `Idea`

A researchable proposal derived from one or more signals.

Lifecycle:

```text
open -> claimed -> researching -> awaiting_decision -> promoted | rejected
```

#### `ResearchSession`

An investigation run by an agent against an idea.

#### `Finding`

A research conclusion that may later support or refute a hypothesis.

### 7.3 Exploratory Objects

#### `Hypothesis`

A falsifiable statement under test.

#### `ArchitectureRelation`

Graph edge between initiatives or hypotheses.

Useful relation types:

- depends_on
- alternative_to
- supersedes
- derived_from
- validates
- refutes
- composes_with

### 7.4 Execution Objects

#### `Milestone`

A trackable checkpoint inside an initiative.

#### `Task`

A unit of work that an agent can claim and execute.

#### `Agent`

An identified local or remote coding agent.

Important attributes:

- owner human
- device
- agent type
- capabilities
- active session
- permissions

#### `WorkSession`

One bounded agent session.

#### `StateBranch`

DBay branch used for shared collaborative state.

#### `CodeBranch`

Git branch used for code changes.

### 7.5 Evidence and Governance Objects

#### `Artifact`

Metadata around an output:

- report
- commit
- PR
- diagram
- log
- benchmark output

#### `MetricRun`

One benchmark or evaluation execution.

#### `MetricResult`

One named output from a metric run.

#### `Feedback`

Human input directed at an idea, initiative, branch, task, or agent.

#### `Decision`

Formal state-changing judgment:

- adopt
- reject
- pause
- pivot
- merge
- supersede

## 8. Main Workflows

### 8.1 From Article to Initiative

```text
human sees article
  -> posts signal + idea on blackboard
  -> agent claims idea
  -> agent opens research session
  -> agent publishes findings and recommendation
  -> human reviews
  -> idea rejected, attached to existing initiative, or promoted
```

### 8.2 From Initiative to Code

```text
initiative
  -> hypothesis
  -> milestone
  -> task
  -> state branch
  -> Git branch
  -> implementation
  -> metric run
  -> evidence
  -> decision
```

### 8.3 Agent Session Start

Every agent should:

1. Load project-main accepted state.
2. Load relevant track branch state.
3. Load active initiatives and open ideas.
4. Search peer WIP and recent findings.
5. Check GitHub branch and PR context.
6. Only then claim a task or idea.

### 8.4 Agent Handoff

When ending a session, an agent should publish:

- current status
- findings
- touched files
- associated Git branch
- benchmark outputs
- blockers
- next recommended step

### 8.5 Human Feedback

Human feedback should be typed:

- instruction
- opinion
- question
- correction
- priority change
- formal decision

Agents consume this through the local MCP client and adapt their plan.

## 9. Human Console

### 9.1 Blackboard

Supports:

- goals
- directives
- ideas
- feedback
- decisions

### 9.2 Architecture Graph

Visualizes:

- track
- initiative
- hypothesis
- branch
- relation edges
- current state
- latest metrics

### 9.3 Idea Inbox

Shows:

- open ideas
- claimed ideas
- research status
- awaiting decision

### 9.4 Agent Workboard

Shows:

- agent identity
- owner
- current work
- branch
- status
- blockers
- heartbeat

### 9.5 Metrics and Evidence

Shows:

- latest scores
- baseline
- delta
- commit
- branch
- evaluator
- confidence / validity

## 10. Local Collaboration Client

### 10.1 Required Components

- MCP server
- local daemon
- CLI
- Git scanner
- runner scanner
- offline queue
- identity/auth module

### 10.2 Required MCP Surface

Read:

- `collab.get_project_context`
- `collab.list_active_initiatives`
- `collab.list_open_ideas`
- `collab.search_peer_work`
- `collab.read_feedback`

Write:

- `collab.claim_idea`
- `collab.start_research_session`
- `collab.report_status`
- `collab.publish_finding`
- `collab.publish_artifact`
- `collab.attach_metric`
- `collab.request_decision`
- `collab.claim_task`

## 11. GitHub Integration

The system should ingest:

- commits
- branches
- pull requests
- reviews
- merge events
- CI results

It should also maintain explicit links:

```text
initiative <-> Git branch
task <-> commit
metric run <-> commit
decision <-> PR
```

## 12. Concurrency Model

The collaboration system must support:

- many readers
- many writers
- concurrent agent sessions
- offline laptops reconnecting later
- conflicting branch-local findings

Recommended principles:

1. Use append-only events for important state changes.
2. Keep formal decisions explicit and versioned.
3. Prefer branch-local writes during exploration.
4. Promote upward only through deliberate merge or decision.
5. Avoid silently overwriting accepted state.

## 13. What This Means for DBay

DBay would need to evolve from "memory store" toward a typed collaborative state
substrate with:

1. branch-aware state
2. typed objects and relations
3. event log
4. promotion and merge semantics
5. access control
6. cross-device synchronization
7. support for branch-local and global queries
8. APIs for both human UI and agent MCP clients

This workspace is therefore a good proving ground for the broader DBay thesis:
single-agent memory can often remain local, but multi-agent coordination with
concurrent writes needs a centralized, cloud-backed shared state system.

## 14. Non-Goals

At least initially, the system should not attempt to:

- replace GitHub
- replace IDEs
- replace every project management tool
- store all raw artifact payloads directly
- force every idea to become a task
- treat every agent thought as globally accepted truth

## 15. Suggested MVP

### MVP 1

- project / track / initiative / idea / agent / feedback / decision objects
- blackboard
- idea inbox
- agent workboard
- GitHub sync
- DBay state branches
- MCP client surface for agents

### MVP 2

- architecture graph
- metrics panel
- branch-local findings
- promotion flow from idea to initiative

### MVP 3

- richer merge semantics
- offline replay
- recommendation engine for reuse
- automatic detection of duplicate work

## 16. Summary

The system should be understood as:

```text
GitHub = code truth
Shared State Layer = collaboration truth
DBay = implementation of the Shared State Layer
Web console = human control surface and primary conversation surface
Local client = agent edge connector
```

DBay branches are central to the design because exploratory architecture work
needs branch-local collaborative state before any conclusion becomes global
project truth.
