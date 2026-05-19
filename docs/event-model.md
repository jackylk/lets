# Event Model

## 1. Purpose

This document defines the minimum event model required for the collaboration
workspace.

The system should use events to preserve:

- provenance
- auditability
- temporal reconstruction
- concurrent write safety
- derived views

## 2. Event Design Principles

1. Important state transitions should be append-only events.
2. Current UI state should be derived from events plus projections.
3. Every event must carry actor, branch, target, and timestamp.
4. Events should preserve enough context for audit and replay.
5. Humans and agents use the same event system.

## 3. Common Event Envelope

```json
{
  "id": "evt_...",
  "project_id": "proj_...",
  "state_branch_id": "branch_...",
  "event_type": "idea.claimed",
  "actor_type": "agent",
  "actor_id": "agent_...",
  "target_type": "idea",
  "target_id": "idea_...",
  "occurred_at": "2026-05-18T10:30:00Z",
  "payload": {},
  "correlation_id": "optional",
  "causation_id": "optional"
}
```

## 4. Event Categories

### 4.1 Project and Goal Events

```text
project.created
goal.created
goal.updated
goal.archived
track.created
track.updated
```

### 4.2 Signal and Idea Events

```text
signal.created
idea.created
idea.claimed
idea.released
idea.research_started
idea.awaiting_decision
idea.promoted
idea.rejected
idea.archived
```

### 4.3 Research Events

```text
research_session.started
research_session.updated
research_session.completed
finding.created
finding.updated
finding.promoted
finding.rejected
```

### 4.4 Initiative and Architecture Events

```text
initiative.created
initiative.status_changed
hypothesis.created
hypothesis.updated
hypothesis.status_changed
architecture_relation.created
architecture_relation.removed
```

### 4.5 Task and Work Events

```text
task.created
task.claimed
task.started
task.blocked
task.unblocked
task.completed
work_session.started
work_session.heartbeat
work_session.status_changed
work_session.completed
```

### 4.6 Branch Events

```text
state_branch.created
state_branch.archived
state_branch.item_promoted
state_branch.item_superseded
code_branch.linked
code_branch.unlinked
```

### 4.7 Artifact and Metric Events

```text
artifact.published
metric_run.started
metric_run.completed
metric_result.recorded
```

### 4.8 Human Governance Events

```text
feedback.created
feedback.updated
decision.created
decision.superseded
```

### 4.9 GitHub Sync Events

```text
github.branch_discovered
github.commit_ingested
github.pull_request_opened
github.pull_request_updated
github.pull_request_merged
github.ci_status_changed
```

## 5. Event Examples

### 5.1 Idea Claimed

```json
{
  "event_type": "idea.claimed",
  "actor_type": "agent",
  "actor_id": "agent_codex_jacky",
  "target_type": "idea",
  "target_id": "idea_topic_wm",
  "payload": {
    "claimed_by_agent_id": "agent_codex_jacky"
  }
}
```

### 5.2 Finding Promoted

```json
{
  "event_type": "finding.promoted",
  "actor_type": "human",
  "actor_id": "human_jacky",
  "target_type": "finding",
  "target_id": "finding_attention_dilution",
  "payload": {
    "from_branch_id": "session_codex_001",
    "to_branch_id": "initiative_topic_wm"
  }
}
```

### 5.3 Metric Run Completed

```json
{
  "event_type": "metric_run.completed",
  "actor_type": "agent",
  "actor_id": "agent_echomem_cc",
  "target_type": "metric_run",
  "target_id": "metric_locomo_r9",
  "payload": {
    "dataset": "locomo",
    "overall": 0.7641,
    "baseline": 0.7656,
    "delta": -0.0015,
    "commit_sha": "abc123"
  }
}
```

## 6. Required Projections

Derived read models should include:

### 6.1 Active Agent View

From:

- work_session.started
- work_session.heartbeat
- work_session.status_changed
- work_session.completed

### 6.2 Idea Inbox View

From:

- idea.created
- idea.claimed
- idea.research_started
- idea.awaiting_decision
- idea.promoted
- idea.rejected

### 6.3 Architecture Graph View

From:

- initiative.created
- hypothesis.created
- architecture_relation.created
- initiative.status_changed
- hypothesis.status_changed

### 6.4 Metrics View

From:

- metric_run.completed
- metric_result.recorded

### 6.5 Human Attention Queue

From:

- idea.awaiting_decision
- feedback.created
- task.blocked
- metric_run.completed

## 7. Event vs Current State

### Must Be Events

- formal decisions
- promotion
- rejection
- claim / release
- status transitions
- GitHub ingestion
- metrics completion

### Can Be Current State Only

- denormalized counts
- cached latest metric
- last heartbeat materialization
- UI convenience summaries

## 8. Idempotency and Concurrency

Events should support:

- idempotency key
- optimistic conflict checks
- correlation IDs
- causal chains

Recommended patterns:

- duplicate GitHub webhook -> deduplicate by source event ID
- repeated heartbeat -> append or coalesce depending on storage cost
- conflicting claim attempts -> only one accepted claim event

## 9. Retention

### Keep Long Term

- decisions
- promotions
- metric events
- GitHub events
- architecture changes

### Possibly Compact

- frequent heartbeat events
- repeated status pings
- low-value transient updates

## 10. Open Questions

1. Whether heartbeat should be event-sourced or partially ephemeral.
2. Whether projections live inside DBay or a separate service.
3. Whether branch inheritance should be encoded in event replay.
4. Whether idea promotion emits one event or a transaction bundle.
5. Whether GitHub webhook payloads should be stored raw or normalized only.

