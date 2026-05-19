# Goal Guardian Design (v1.5c-2)

> **Status:** approved 2026-05-19 (brainstorm), ready for implementation plan
> **Replaces:** roadmap §3 (v1.5c "Goal Guardian" line items)
> **Estimated effort:** ~1 week (backend ~3 days, frontend ~2 days, dogfood tuning ~ongoing)

## 1. Goals

Make Lets the only multi-agent workspace that **gently keeps conversations on topic**. Three concrete capabilities:

1. **Goal** — each topic can declare an explicit target Artifact + spec (separate from the topic title). Approved by team. Visible in context pane.
2. **Task Tree** — under each goal, a hierarchical task list (true tree, not flat list). Items have status (pending/active/done) and optional owner (human OR agent).
3. **Drift Nudge** — when conversation drifts from the active task, the agent that notices posts a `nudge` typed message offering three actions: spin off as new topic, return to main thread, or dismiss.

This is roadmap §3 "v1.5c L2 Goal Guardian" line items, scoped down to what's testable in 1 week.

## 2. Non-Goals

- **No backend drift-detection algorithm.** Agents decide when to nudge using their own LLM judgment. Backend supplies the data they need to judge (last nudge timestamp, active task, topic mode) and that's it.
- **No semantic similarity / embeddings.** Out of scope. If agents over- or under-nudge, we tune skill prompts, not code.
- **No goal editing in v1.5c-2 UI.** Goal is set via `goal_proposal` → adopt flow. Changing it = `goal_proposal` v2 → adopt. No standalone edit form.
- **No advanced task editing.** Two actions only: check a task done, add a new task. Title/owner changes go through conversation ("@claude please assign Demo prep to me"). No drag-to-reorder, no inline edit, no delete.
- **No multi-version task trees.** One `task_tree` per topic (1:1). `task_tree_proposal` messages that get adopted replace the existing tree (versioned via `version` column for audit, but only one active).
- **No `task_tree` change history UI.** Audit columns exist on the row; viewing diffs is a future enhancement.
- **No automatic move of past messages on "spin off."** Spin-off = creates a fresh topic with an agent-written summary. Original messages stay in original topic. Conversation log is append-only.

## 3. Architecture

Three new tables, six new REST endpoints, four new MCP tools, one extension to existing `topic_stream` response, and frontend wiring for the three components already rendered in mock form.

```
┌─ Backend ─────────────────────────────────────────────────┐
│                                                            │
│  task_trees ──1:N──> task_items (self-referencing tree)   │
│      │                                                     │
│      └── topic_id (UNIQUE)                                 │
│                                                            │
│  drift_nudges                                              │
│      ├── nudge_message_id ──→ messages                     │
│      └── resolved_to_topic_id ──→ topics (nullable)        │
│                                                            │
│  topics.mode {exploratory | actionable} ← new column       │
│                                                            │
└────────────────────────────────────────────────────────────┘

Agent side (MCP):                      Frontend side (REST):
  propose_goal                           POST /api/topics/{id}/goal
  propose_task_tree                      POST /api/topics/{id}/task-tree
  update_task_status                     PATCH /api/task-items/{id}
  post_nudge                             POST /api/task-items
                                         GET /api/topics/{id}/task-tree
                                         POST /api/nudges/{id}/resolve

Both consume the same GET /api/topics/{id}/messages, now returning
{messages: [...], drift_context: {...}}
```

### 3.1 Why each piece

| Piece | Why it has to exist |
|-------|---------------------|
| `task_trees` table separate from `topics` | A topic that hasn't yet had a tree approved still needs to exist (mode=exploratory). `task_trees.topic_id UNIQUE` enforces 1:1 only after adoption. |
| `task_items` self-referencing FK | Q3 decision: true tree UI, not flat. `parent_item_id` nullable for root items. |
| `drift_nudges` table | Need stateful "last nudge at" to expose to agents via `drift_context` so they don't spam. Without this, agents have no memory between calls. |
| `topics.mode` column | Q5 needs it — drift detection only fires on `actionable` topics. |
| `drift_context` in topic_stream response | Q5 decision: agents read drift state alongside messages, no extra round trip. |

## 4. Schema

### 4.1 `topics` (extend)

```sql
ALTER TABLE topics ADD COLUMN mode TEXT NOT NULL DEFAULT 'exploratory'
    CHECK (mode IN ('exploratory', 'actionable'));
```

Default `exploratory` matches the "don't nudge me until we've committed to a goal" semantics. UI for switching mode is **not in this spec** (future enhancement); agents can flip it via a future MCP tool. Drift detection only runs when `mode = 'actionable'`.

### 4.2 `task_trees`

```sql
CREATE TABLE task_trees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL UNIQUE,
    goal_artifact_id INTEGER,
    goal_spec_text TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    approved_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    approved_by_human_id INTEGER,
    proposal_message_id INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (topic_id) REFERENCES topics(id),
    FOREIGN KEY (goal_artifact_id) REFERENCES artifacts(id),
    FOREIGN KEY (approved_by_human_id) REFERENCES humans(id),
    FOREIGN KEY (proposal_message_id) REFERENCES messages(id)
);
CREATE INDEX idx_task_trees_topic ON task_trees(topic_id);
```

When an agent's `task_tree_proposal` message is adopted, a row is inserted here. Subsequent adoptions on the same topic UPDATE the row (incrementing `version`) and DELETE-then-INSERT the items (simple semantics; we keep the audit trail in messages, not in a history table).

### 4.3 `task_items`

```sql
CREATE TABLE task_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_tree_id INTEGER NOT NULL,
    parent_item_id INTEGER,
    title TEXT NOT NULL,
    owner_human_id INTEGER,
    owner_agent_instance_id INTEGER,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'active', 'done')),
    position INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_tree_id) REFERENCES task_trees(id),
    FOREIGN KEY (parent_item_id) REFERENCES task_items(id),
    FOREIGN KEY (owner_human_id) REFERENCES humans(id),
    FOREIGN KEY (owner_agent_instance_id) REFERENCES agent_instances(id),
    CHECK (
        (owner_human_id IS NULL AND owner_agent_instance_id IS NULL)
        OR (owner_human_id IS NOT NULL AND owner_agent_instance_id IS NULL)
        OR (owner_human_id IS NULL AND owner_agent_instance_id IS NOT NULL)
    )
);
CREATE INDEX idx_task_items_tree ON task_items(task_tree_id, position);
CREATE INDEX idx_task_items_parent ON task_items(parent_item_id);
```

The `CHECK` constraint enforces owner is exactly one of {none, human, agent}.

`position` is sort order within siblings (same `parent_item_id` + same `task_tree_id`). Adding a new item appends to the end (max position + 1). No reorder API in v1.5c-2.

### 4.4 `drift_nudges`

```sql
CREATE TABLE drift_nudges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL,
    nudge_message_id INTEGER NOT NULL UNIQUE,
    triggered_by_agent_instance_id INTEGER,
    drift_window_start_message_id INTEGER,
    drift_window_end_message_id INTEGER,
    drift_summary TEXT,
    resolved_at TEXT,
    resolved_by TEXT CHECK (resolved_by IN ('moved_to_topic', 'returned', 'dismissed')),
    resolved_to_topic_id INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (topic_id) REFERENCES topics(id),
    FOREIGN KEY (nudge_message_id) REFERENCES messages(id),
    FOREIGN KEY (triggered_by_agent_instance_id) REFERENCES agent_instances(id),
    FOREIGN KEY (resolved_to_topic_id) REFERENCES topics(id)
);
CREATE INDEX idx_drift_nudges_topic ON drift_nudges(topic_id, created_at DESC);
```

Every `nudge` typed message must have a corresponding `drift_nudges` row (created in the same transaction when an agent calls `post_nudge`). This is what lets us answer "when was the last nudge on this topic?" without scanning messages.

## 5. API surface

### 5.1 Frontend REST

**`POST /api/topics/{topic_id}/goal`** — adopt a goal proposal

Body: `{ goal_proposal_message_id: int }` OR `{ artifact_id: int|null, spec_text: str }`

- If `goal_proposal_message_id` given, the goal is extracted from that message's metadata and the message becomes the audit trail.
- If direct args given, the goal is set without referencing a proposal (used when a human types a goal directly into a future UI, not in v1.5c-2 scope).
- Either way: upserts the `task_trees` row for this topic (or creates a stub with no items if none exists), setting `goal_artifact_id` and `goal_spec_text`.

Auth: session cookie (human action).

**`POST /api/topics/{topic_id}/task-tree`** — adopt a task tree proposal

Body: `{ proposal_message_id: int }`

- Reads `metadata.title`, `metadata.items` from the referenced `task_tree_proposal` message.
- Upserts `task_trees` row (increment `version` if exists, set `proposal_message_id`, `approved_by_human_id` from session).
- DELETE all existing `task_items` for this tree, INSERT new ones from the proposal's metadata, preserving hierarchy (proposal items can have `parent_index` referring to another item by 0-based index in the list).

Auth: session cookie.

**`GET /api/topics/{topic_id}/task-tree`** — read current tree

Returns:
```json
{
  "tree": { "id": ..., "version": 2, "goal_artifact_id": ..., "goal_spec_text": "..." },
  "items": [
    { "id": 1, "parent_item_id": null, "title": "P0 outline", "status": "done", "owner": {...}, "position": 0 },
    { "id": 2, "parent_item_id": 1, "title": "structure 8 sections", "status": "done", "owner": {...}, "position": 0 },
    ...
  ]
}
```

If no tree exists yet, returns `{tree: null, items: []}`.

Auth: any (Bearer or session).

**`POST /api/task-items`** — add a new item

Body: `{ task_tree_id, parent_item_id?, title, owner_human_id?, owner_agent_instance_id? }`

Returns the inserted item row. `position` is computed server-side (max existing + 1 within siblings).

Auth: session cookie OR Bearer (agents can add via MCP too).

**`PATCH /api/task-items/{id}`** — change status or title

Body: `{ status?: 'pending'|'active'|'done', title?: string }`

Other fields (owner, parent, position) are not editable via this endpoint in v1.5c-2.

Auth: session cookie OR Bearer.

**`POST /api/nudges/{id}/resolve`** — mark a nudge handled

Body: `{ resolved_by: 'moved_to_topic'|'returned'|'dismissed', spinoff_title?: string }`

- `moved_to_topic`: requires `spinoff_title`. Creates a new topic in the same project, copies the nudge's `drift_summary` into a `system` typed message ("从 [T-XXX] 迁移而来。摘要：..."), updates the nudge's `resolved_to_topic_id`, returns `{ resolved: true, new_topic_id: int }`.
- `returned`: marks resolved, no side effects.
- `dismissed`: marks resolved, no side effects. (Agents are expected to respect "dismissed" by not nudging again in the same drift window; tracked by the agent reading `drift_context.last_nudge_resolved_by`.)

Auth: session cookie.

### 5.2 Agent MCP tools

**`propose_goal(topic_id, spec_text, artifact_id?)`**

Posts a `goal_proposal` typed message. Body is `spec_text`. Metadata is `{ artifact_id, spec_text, proposed_at }`. Does NOT write to `task_trees` (human must adopt).

**`propose_task_tree(topic_id, title, items)`**

`items` is a list of `{ title, parent_index?: int, owner?: { kind: 'human'|'agent', id: int } }`.

Posts a `task_tree_proposal` typed message. Body is a human-readable summary ("提议把这个 PPT 拆成 7 个任务"). Metadata is `{ title, items: [...] }` exactly mirroring the existing frontend `TaskTreeProposalMeta` type.

**`update_task_status(item_id, status)`**

Updates `task_items.status`. Used by agents to claim work (status='active') and report completion (status='done'). Posts a `status` typed message as side effect for stream visibility ("agent X started: <title>" / "agent X finished: <title>").

**`post_nudge(topic_id, reason, drift_summary, window_start_msg_id, window_end_msg_id)`**

Single transaction:
1. INSERT a `nudge` typed message with body = `reason`, metadata = `{ reason, drift_summary }`
2. INSERT a `drift_nudges` row referencing that message

Returns `{ nudge_message_id, drift_nudge_id }`.

The agent should only call this after consulting `drift_context` in the topic_stream response and confirming `last_nudge_resolved_by != 'dismissed'` since `last_nudge_at`.

### 5.3 `GET /api/topics/{topic_id}/messages` response extension

Existing response shape:
```ts
MessageDTO[]
```

New response shape:
```ts
{
  messages: MessageDTO[],
  drift_context: {
    topic_mode: "exploratory" | "actionable",
    active_task: { id: number, title: string } | null,
    last_nudge_at: string | null,        // ISO timestamp
    last_nudge_message_id: number | null,
    last_nudge_resolved_by: "moved_to_topic" | "returned" | "dismissed" | null,
    messages_since_last_nudge: number,
  }
}
```

`active_task` = the single `task_items` row with `status='active'` for this topic's tree (if multiple, the first by `position`; we don't enforce single-active in v1.5c-2 because it complicates the "claim" flow).

`messages_since_last_nudge` = count of messages with `id > last_nudge_message_id` in this topic, or total message count if no prior nudge.

**Frontend migration**: `useTopicMessages` returns `data.messages` and exposes `data.drift_context` separately. All existing consumers of `data` (a `MessageDTO[]`) need one-line edits to `data.messages`.

## 6. Frontend changes

### 6.1 `TaskTreePanel` (already exists, currently read-only flat list)

Replace its hardcoded items with `useTopicTaskTree(topicId)` query. Render hierarchy:

- Items with `parent_item_id = null` at root indent
- Children indented `position * 16px`
- Each row: checkbox (`status === 'done'`) + title + (owner avatar) + caret if has children (collapse/expand)
- Bottom of panel: "+ 加任务" button → inline input → POST /api/task-items
- Expand/collapse state lives in component-local `useState<Set<number>>` (no persistence in v1.5c-2)

Toggling checkbox PATCHes status pending ↔ done. Single-active enforcement is out of scope.

### 6.2 `NudgeMessage` (already exists in stream)

Replace static placeholder with three buttons:

- **独立成新 topic** (primary) → opens `<SpinoffDialog>` modal with title prefilled from `drift_summary`, submit → `POST /api/nudges/{id}/resolve` with `moved_to_topic` → navigate to new topic
- **回主线** → `POST /api/nudges/{id}/resolve` with `returned` → button row disappears
- **略过** → `POST /api/nudges/{id}/resolve` with `dismissed` → button row disappears, nudge stays grey-italic in stream

If `drift_nudges.resolved_at IS NOT NULL`, render the nudge with a small footer line: "已处理：迁移到 [T-XXX]" or "已处理：回主线" or "已处理：略过", no buttons. The nudge component fetches its own resolved state by including the `drift_nudge` id in the message metadata (set by `post_nudge` MCP tool).

### 6.3 `TaskTreeProposalMessage` (already exists)

Add "Adopt as task tree" button below the rendered task list.

- Disabled if a task_tree already exists at the same or newer version (frontend reads version from `useTopicTaskTree`)
- On click → `POST /api/topics/{id}/task-tree` with `proposal_message_id = this message id` → invalidate `useTopicTaskTree` query

### 6.4 `goal_proposal` rendering (new typed message UI)

Currently `goal_proposal` is in the type union but has no dispatch case. Add:

- `frontend/src/messages/GoalProposalMessage.tsx` — similar look to spec_change (border, "目标" tag, render proposed artifact + spec). Button: "Adopt as goal" → `POST /api/topics/{id}/goal`
- Add to `Message.tsx` dispatch
- Add to actorResolver (no change needed; it's a typed message)

### 6.5 `GoalDetailPanel` (already exists, hardcoded)

Replace hardcoded artifact/spec/approvers with data from `useTopicTaskTree` (returns the `task_trees` row including `goal_artifact_id` and `goal_spec_text`). When `tree === null`, render empty state "尚未设定目标".

## 7. Drift detection: agent-side discipline

This spec ships the **data plumbing** for drift detection. The actual judgment lives in agent skills. v1.5c-2 also ships a skill update:

### 7.1 New skill: `lets-goal-guardian`

Skill file at `.claude/skills/lets-goal-guardian/SKILL.md` (committed as part of this work):

```
When working in a Lets topic:

1. On every reply, read the topic_stream response's `drift_context` field.

2. If `topic_mode == "exploratory"`, never post a nudge. Stay quiet.

3. If `topic_mode == "actionable"` AND `active_task.title` exists:
   - Look at the last 3-5 messages in the topic.
   - If they discuss something clearly unrelated to `active_task.title`
     AND `messages_since_last_nudge >= 3`
     AND (`last_nudge_at` is null OR more than 5 minutes ago OR
          `last_nudge_resolved_by` was "returned" — NOT "dismissed"),
     then call `post_nudge` with a brief drift_summary
     summarizing what the off-topic discussion is about
     (so the user can spin it off if they want).

4. If `last_nudge_resolved_by == "dismissed"`, do not nudge again on this
   topic until conversation goes through a clear topic-shift signal
   (e.g., a question on a totally different subject).

5. Tone: "温和提醒" — never blame, always offer the spinoff path first.
```

Codex gets the same skill committed under its skill directory.

### 7.2 How frequency tuning works

Dogfood will surface false-positives ("agent nudged me when I wasn't off topic") and false-negatives ("we talked off topic for 10 min and no nudge"). Tune by editing the skill text, not the code. The skill is itself an artifact subject to `spec_change` flow — meta, but consistent with the rest of Lets.

## 8. Implementation order

(Detailed task breakdown belongs to the implementation plan; this is the high-level sequence.)

1. **Schema migration** (Day 1): add `topics.mode`, create `task_trees` / `task_items` / `drift_nudges`. Idempotent migration helpers like the existing `_migrate_humans_github`.
2. **REST endpoints + tests** (Day 1-2): all six new routes with pytest coverage of session-cookie + Bearer-token paths.
3. **MCP tools + tests** (Day 2): four new tools registered in `app/mcp_server.py`. Each tool gets a pytest that invokes it through the MCP transport and verifies side effects.
4. **`topic_stream` extension** (Day 2): break the existing response shape; update all backend callers + 1 frontend hook. Add tests for `drift_context` content under various states.
5. **Frontend `useTopicTaskTree` + TaskTreePanel rewrite** (Day 3): real data, tree rendering, checkbox, add-row.
6. **Frontend NudgeMessage interactions + SpinoffDialog** (Day 3): three buttons + modal + invalidation.
7. **Frontend TaskTreeProposalMessage adopt button + GoalProposalMessage component** (Day 3-4): two new typed message UIs (one new file, one button on existing).
8. **Frontend GoalDetailPanel wired to real data** (Day 4): replace hardcoded fixture content.
9. **`lets-goal-guardian` skill** (Day 4): commit skill file to `.claude/skills/`.
10. **End-to-end test** (Day 5): a pytest scenario where agent A starts a topic in actionable mode, posts task_tree_proposal, human adopts, conversation drifts, agent B posts nudge, human spins off into new topic. Verify all four tables get the expected rows.
11. **Playwright E2E** (Day 5): user adopts a `task_tree_proposal` from fixture seed, checks a box, the panel updates. Spin off a nudge into a new topic and verify navigation.

## 9. Open questions deferred to implementation

- **Position-shifting on add**: when a new item is added with a `parent_item_id`, what's its position? Currently spec says "max sibling + 1". OK for v1.5c-2.
- **Cascade on delete**: not in v1.5c-2 (no delete endpoint).
- **Concurrent task_tree adoption**: two humans hit "Adopt as task tree" within the same second. SQLite-level: last-write-wins, both increment `version`. Acceptable for v1.5a/b user counts.
- **Goal artifact must exist?**: `goal_proposal` lets agents propose a goal pointing at an artifact that doesn't exist yet (FK is nullable). Adopt validates that if `goal_artifact_id` is given, the artifact exists. If not given, the goal is "spec-only" (`goal_spec_text` is the goal).

## 10. Success criteria

End of week, the following dogfood scenario works against the Railway deploy:

1. Neo opens a topic in `actionable` mode.
2. claude posts a `task_tree_proposal` with 5 nested items (1 has 3 children).
3. Neo clicks "Adopt as task tree" → tree visible in context pane with tree indent.
4. Neo and claude discuss for ~10 minutes about an unrelated topic (friday team dinner).
5. codex (a different agent instance) reads `drift_context`, decides this is drift, calls `post_nudge` with a `drift_summary` summarizing the team-dinner thread.
6. The nudge renders inline with three buttons.
7. Neo clicks "独立成新 topic" → SpinoffDialog opens with title prefilled "周五团建" → submits.
8. A new topic is created, system message says "从 T-PPT 迁移而来。摘要：讨论周五团建的时间和地点。"
9. Neo navigates to the new topic; original PPT topic shows the nudge as "已处理：迁移到 [T-XXX]".
