# MVP Scope

## MVP Goal

Build the smallest system that proves both:

1. teams need an agent-native R&D workspace
2. multi-agent collaboration benefits from centralized, branch-aware shared state

## Product Promise for MVP

A team member can post an idea on a blackboard, an agent can claim and research
it, multiple agents can coordinate around related work, humans can see current
architecture paths and benchmark evidence, and final code still lands through
GitHub.

## In Scope

### 1. Blackboard

Supports:

- create goal
- create idea
- create feedback
- create decision
- target an existing initiative, branch, task, or agent

### 2. Idea Inbox

Supports:

- source URL
- freeform idea text
- desired output
- claim by agent
- research status
- findings
- promote to initiative
- reject / archive

### 3. Agent Workboard

Shows:

- agent name
- human owner
- device
- active session
- current initiative
- current task
- state branch
- Git branch
- latest status
- blocker
- heartbeat

### 4. Architecture Graph

Supports:

- track nodes
- initiative nodes
- hypothesis nodes
- relation edges
- current status
- latest evidence summary

### 5. Branch-aware Shared State

Required DBay scopes:

- `project-main`
- `track-*`
- `initiative-*`
- `session-*`

Required actions:

- create branch
- read inherited context
- append local state
- promote finding upward
- archive branch

### 6. GitHub Integration

Ingest:

- repo
- branch
- commit
- PR
- CI state

Required links:

- initiative -> Git branch
- task -> commit
- metric run -> commit
- decision -> PR

### 7. Metrics

Support:

- metric run
- metric result
- baseline
- delta
- config
- commit binding
- branch binding

Initial target:

- LoCoMo
- PersonaMem
- test pass/fail

## Out of Scope for MVP

- custom IDE
- embedded code editor
- terminal replacement
- model routing
- autonomous task decomposition engine
- rich enterprise permissioning
- generalized project management
- raw artifact storage
- automatic code merge

## Core Objects

### Strategic

- Project
- Goal
- Track
- Initiative
- Hypothesis

### Intake

- Signal
- Idea
- ResearchSession
- Finding

### Execution

- Agent
- WorkSession
- Task
- StateBranch
- CodeBranch

### Evidence and Governance

- Artifact
- MetricRun
- MetricResult
- Feedback
- Decision

## Minimal Relationships

```text
Project contains Track
Track contains Initiative
Initiative tests Hypothesis
Idea may promote to Initiative
ResearchSession investigates Idea
Finding informs Initiative or Hypothesis
Agent opens WorkSession
WorkSession executes Task
Task works on StateBranch and CodeBranch
MetricRun evaluates CodeBranch
Feedback targets Idea / Initiative / Task / Branch / Agent
Decision governs Idea / Initiative / Hypothesis / Branch
```

## MVP Screens

### Overview

- current goals
- active initiatives
- human attention needed
- latest metrics
- active agents
- open ideas

### Blackboard

- create idea
- create feedback
- create decision
- recent human inputs

### Ideas

- open
- claimed
- researching
- awaiting decision
- promoted / rejected

### Architecture

- graph view
- node detail drawer
- latest evidence

### Agents

- current sessions
- current work
- blockers
- heartbeat

### Initiative Detail

- hypothesis
- linked state branch
- linked Git branches
- findings
- metrics
- decisions

## MVP Agent MCP API

### Read

- `collab.get_project_context`
- `collab.list_open_ideas`
- `collab.list_active_initiatives`
- `collab.get_initiative_context`
- `collab.search_peer_work`
- `collab.read_feedback`

### Write

- `collab.claim_idea`
- `collab.start_research_session`
- `collab.publish_finding`
- `collab.report_status`
- `collab.claim_task`
- `collab.publish_artifact`
- `collab.attach_metric`
- `collab.request_decision`
- `collab.promote_finding`

## Local Client MVP

### Must Have

- user authentication
- agent registration
- MCP server
- session heartbeat
- local cache
- Git scanner
- benchmark result publisher

### Nice to Have Later

- background file watcher
- local UI tray
- peer-to-peer artifact transfer
- local task launcher

## DBay Capabilities Required

### Already Aligned With DBay Direction

- persistent shared storage
- cross-session recall
- branch concepts

### Likely New or More Formalized

- typed collaboration objects
- event log
- branch promotion semantics
- branch inheritance queries
- object-level relations
- human feedback and decision objects
- metric attachment
- agent session lifecycle
- ACLs across humans, agents, and projects

## Suggested Delivery Sequence

### Phase 1: Shared State Backbone

- object schema
- branch model
- event model
- agent registration
- basic MCP API

### Phase 2: Human Workspace

- blackboard
- idea inbox
- agent workboard
- initiative detail

### Phase 3: Technical Evidence

- GitHub integration
- metric run ingestion
- LoCoMo / PersonaMem binding
- architecture graph

### Phase 4: Real Team Trial

- use it on `echomem`
- onboard at least one teammate
- run with several local agents
- measure duplicated work avoided
- measure speed from idea to decision

## MVP Validation Questions

### Product Questions

1. Do humans check the workspace before pinging agents manually?
2. Do agents reuse peer findings before starting duplicate work?
3. Does idea intake become a natural habit?
4. Does the architecture graph improve understanding versus markdown?
5. Does the team make better route decisions with metric-linked evidence?

### DBay Questions

1. Are state branches useful in real work?
2. Which objects truly need to be typed?
3. How often are findings promoted across branch levels?
4. What conflicts arise under concurrent agent writes?
5. Which parts of "memory" are actually durable knowledge versus live state?

## Initial Milestones

### M1

Single project, single user, multiple local agents.

Success:

- ideas can be created
- one agent can claim and report findings
- all sessions visible in workboard

### M2

Single project, multiple humans, multiple laptops.

Success:

- shared blackboard
- agent sessions visible across devices
- no duplicated idea claims

### M3

Branch-aware exploration.

Success:

- initiative branch created
- findings stay local until promoted
- humans can inspect route-specific evidence

### M4

GitHub and metrics loop.

Success:

- Git branches linked
- PR linked
- LoCoMo / PersonaMem results attached
- decision made from evidence

## MVP Success Definition

The MVP succeeds when a real team can use it for one project and achieve this
workflow without side channels:

1. human posts idea
2. agent claims it
3. agent researches and publishes findings
4. human promotes it
5. another agent reuses those findings on a related implementation branch
6. metrics are published
7. humans decide whether to continue
8. code lands through GitHub

At that point the product thesis and the DBay thesis are both materially proven.
