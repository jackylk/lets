# Core Schema

## 1. Purpose

This document defines the first version of the typed collaboration objects used
by the Agent-native R&D workspace.

The schema should support:

- multiple humans
- multiple local coding agents
- project-level goals
- exploratory architecture paths
- idea intake
- branch-aware shared state
- GitHub linkage
- benchmark evidence
- human feedback and decisions

## 2. Design Principles

1. Use typed objects for collaborative state.
2. Keep large payloads outside the main state store.
3. Preserve links between research state and GitHub code state.
4. Keep globally accepted truth separate from exploratory branch-local state.
5. Prefer append-only events for important state changes.

## 3. Entity Overview

```text
Project
Human
Agent
Goal
Track
Signal
Idea
ResearchSession
Finding
Initiative
Hypothesis
ArchitectureRelation
Milestone
Task
WorkSession
StateBranch
CodeBranch
Artifact
MetricRun
MetricResult
Feedback
Decision
```

## 4. Common Fields

Most entities should have:

```text
id
project_id
created_at
updated_at
created_by
state_branch_id
archived_at
metadata
```

## 5. Entity Definitions

### 5.1 Project

```text
id
name
slug
description
default_state_branch_id
default_git_repo
created_at
updated_at
```

### 5.2 Human

```text
id
name
email
org_id
avatar_url
created_at
updated_at
```

### 5.3 Agent

```text
id
project_id
name
agent_type
owner_human_id
device_id
capabilities
status
last_seen_at
created_at
updated_at
```

### 5.4 Goal

```text
id
project_id
track_id nullable
title
description
metric_target nullable
status
priority
created_by
created_at
updated_at
```

### 5.5 Track

```text
id
project_id
key
title
description
status
owner_human_id nullable
created_at
updated_at
```

### 5.6 Signal

```text
id
project_id
type
source_url nullable
title
summary nullable
raw_ref nullable
created_by
created_at
updated_at
```

### 5.7 Idea

```text
id
project_id
signal_id nullable
track_id nullable
title
question
initial_thought
desired_output
status
claimed_by_agent_id nullable
claimed_at nullable
created_by
created_at
updated_at
```

### 5.8 ResearchSession

```text
id
project_id
idea_id
agent_id
state_branch_id
status
started_at
ended_at nullable
summary nullable
```

### 5.9 Finding

```text
id
project_id
research_session_id nullable
initiative_id nullable
hypothesis_id nullable
title
summary
confidence
finding_type
artifact_id nullable
status
created_by_agent_id nullable
created_by_human_id nullable
created_at
updated_at
```

### 5.10 Initiative

```text
id
project_id
track_id
title
problem
hypothesis_summary
status
owner_human_id nullable
owner_agent_id nullable
state_branch_id
created_at
updated_at
```

### 5.11 Hypothesis

```text
id
project_id
initiative_id
statement
status
success_criteria
created_at
updated_at
```

### 5.12 ArchitectureRelation

```text
id
project_id
from_entity_type
from_entity_id
relation_type
to_entity_type
to_entity_id
created_at
updated_at
```

Supported relation types:

```text
depends_on
alternative_to
supersedes
derived_from
validates
refutes
composes_with
```

### 5.13 Milestone

```text
id
project_id
track_id
initiative_id nullable
key
title
description
status
owner_agent_id nullable
owner_human_id nullable
created_at
updated_at
```

### 5.14 Task

```text
id
project_id
milestone_id nullable
initiative_id nullable
title
description
status
claimed_by_agent_id nullable
claimed_at nullable
state_branch_id nullable
code_branch_id nullable
created_at
updated_at
```

### 5.15 WorkSession

```text
id
project_id
agent_id
task_id nullable
idea_id nullable
initiative_id nullable
state_branch_id
code_branch_id nullable
status
started_at
ended_at nullable
last_heartbeat_at
summary nullable
```

### 5.16 StateBranch

```text
id
project_id
name
branch_type
parent_branch_id nullable
status
created_by
created_at
updated_at
archived_at nullable
```

Branch types:

```text
project_main
track
initiative
session
```

### 5.17 CodeBranch

```text
id
project_id
repo_ref
branch_ref
base_ref
pull_request_ref nullable
status
linked_state_branch_id nullable
created_at
updated_at
```

### 5.18 Artifact

```text
id
project_id
artifact_type
title
uri
content_hash nullable
produced_by_agent_id nullable
produced_by_task_id nullable
produced_by_research_session_id nullable
created_at
updated_at
```

### 5.19 MetricRun

```text
id
project_id
initiative_id nullable
hypothesis_id nullable
code_branch_id nullable
commit_sha nullable
dataset
config_ref
evaluator
status
started_at
finished_at nullable
artifact_id nullable
```

### 5.20 MetricResult

```text
id
metric_run_id
metric_name
value
baseline_value nullable
delta nullable
sample_count nullable
confidence nullable
valid
created_at
```

### 5.21 Feedback

```text
id
project_id
feedback_type
body
target_entity_type
target_entity_id
priority
created_by_human_id
created_at
updated_at
```

Feedback types:

```text
instruction
opinion
question
correction
priority_change
review
```

### 5.22 Decision

```text
id
project_id
decision_type
title
body
target_entity_type
target_entity_id
supersedes_decision_id nullable
made_by_human_id nullable
made_by_agent_id nullable
created_at
updated_at
```

Decision types:

```text
adopt
reject
pause
pivot
merge
promote
supersede
```

## 6. Important Indexes

### Fast lookup

```text
agent(project_id, status)
idea(project_id, status)
initiative(project_id, status)
work_session(project_id, status)
task(project_id, status)
metric_run(project_id, initiative_id, finished_at)
feedback(project_id, target_entity_type, target_entity_id)
```

### Branch-aware lookup

```text
entity(state_branch_id)
state_branch(project_id, branch_type, status)
architecture_relation(project_id, from_entity_type, from_entity_id)
```

## 7. Derived Views

Recommended read models:

- project overview
- active agent board
- open idea inbox
- architecture graph
- latest metrics per initiative
- human attention queue
- branch activity timeline

## 8. Open Questions

1. Whether `Goal` should support arbitrary nesting.
2. Whether `Track` is always required or optional by project.
3. Whether `Finding` should be normalized further into claim + evidence.
4. Whether `ArchitectureRelation` should use a graph-native store or relational
   edges first.
5. Whether `StateBranch` inherits by query-time resolution or materialized
   snapshot.

