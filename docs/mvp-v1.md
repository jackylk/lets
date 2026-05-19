# MVP v1

## Goal

Build the smallest useful system that lets multiple local coding agents on one
developer machine coordinate on one project.

Initial target:

- one human
- one project
- local Claude Code + Codex
- shared collaboration state
- Git repository remains the code workspace

## What v1 Must Enable

1. Human posts an idea or task.
2. Claude Code or Codex can see open work.
3. One agent claims the work.
4. The other agent can see that it is already claimed.
5. Agents can publish status and findings.
6. Human can inspect progress from one web page.
7. Agents can link their work to a Git branch and commit.

## Explicitly Not in v1

- multi-user auth
- teammate onboarding
- architecture graph
- DBay state branches
- full GitHub integration
- event sourcing
- benchmark ingestion
- permissions
- automated promotion flow

Those belong to later versions.

## v1 Product Surfaces

### 1. Blackboard

Human can create:

- idea
- task
- note / feedback

### 2. Workboard

Shows:

- open items
- claimed items
- active agents
- current status
- latest findings

### 3. Agent MCP

Agents can:

- list open work
- claim work
- report status
- publish finding
- read project context
- read peer activity

## v1 Data Model

### Project

```text
id
name
description
```

### WorkItem

```text
id
project_id
type: idea | task
title
body
status: open | claimed | in_progress | done | rejected
created_by
claimed_by_agent_id nullable
claimed_at nullable
git_branch nullable
created_at
updated_at
```

### Agent

```text
id
name
agent_type
status: idle | active | blocked | offline
last_seen_at
```

### StatusUpdate

```text
id
project_id
agent_id
work_item_id nullable
status
message
created_at
```

### Finding

```text
id
project_id
work_item_id nullable
agent_id
title
body
created_at
```

### HumanNote

```text
id
project_id
target_work_item_id nullable
body
created_at
```

## v1 Minimal API

### Human / Web

```text
POST /work-items
GET  /work-items
GET  /agents
GET  /activity
POST /notes
```

### Agent / MCP

```text
collab.get_project_context
collab.list_work_items
collab.claim_work_item
collab.report_status
collab.publish_finding
collab.list_peer_activity
```

## v1 Suggested Flow

```text
human creates work item
  -> agent lists open items
  -> agent claims item
  -> agent reports status
  -> agent publishes findings
  -> human sees progress in web UI
  -> another agent reads peer activity before starting related work
```

## v1 Technical Shape

### Server

- simple web app
- simple API
- persistent DB
- optional DBay backend if convenient

### Client

- MCP server that talks to the API
- one shared MCP config for Claude Code and Codex

### UI

- one-page workboard
- one form to add work
- one activity feed

## DBay Role in v1

Use DBay only if it accelerates delivery.

Required v1 capability is simple shared persistence, not the full future DBay
branch model.

The purpose of v1 is to prove:

- agents will actually consult shared state
- agents will stop duplicating work when they can see peer state
- the human web view is useful day to day

If that works, then v2 can evolve toward:

- branch-aware state
- typed ideas and initiatives
- multi-user support
- metrics
- architecture graph

## v1 Success Test

On this project itself:

1. Create one idea in the UI.
2. Ask Claude Code to claim it.
3. Ask Codex to list work and verify it sees the claim.
4. Claude Code publishes a finding.
5. Codex reads that finding and takes a related but non-overlapping task.
6. Human sees all of that from one page.

If this works smoothly, v1 is successful.

