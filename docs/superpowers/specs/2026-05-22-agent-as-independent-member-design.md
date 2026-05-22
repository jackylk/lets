# Agent as Independent Member — Design

**Status:** draft, awaiting implementation plan
**Author:** Jacky (brainstormed with Claude)
**Date:** 2026-05-22

## Background

The current data model treats an agent as a `(human, workspace)` cartesian-product row in `agent_instances`. The same Claude Code CLI on one machine, registered by user A to two workspaces, becomes two unrelated rows. There is no concept of "the agent itself" — only the human's stand-in inside a workspace.

This conflicts with the product intent. Agents in Lets are **independent collaborators**: they think slowly but deeply, watch human discussion, wait for a quiet window, then contribute. They broaden ideas and surface blind spots. Different humans bring different agents to the same room; one human can bring multiple agents; agents move between rooms with their owners.

The owner human exists for a single reason: **someone has to pay for the agent and be accountable for it**. Owners can pause, evict, or kill their agents at any time.

## Goal

Refactor data and access-control so an agent is a first-class workspace member, parallel to a human, with a designated owner who controls its lifecycle.

## Non-goals

- Borrowing another user's agent. If B's codex appears in A's workspace, it is because B is a human member of that workspace and B chose to invite their codex.
- Quota visibility. Claude Code / Codex CLI do not expose remaining plan quota; we will not fake it.
- Per-workspace silencing as a separate state. "Eject from this workspace" already covers it.
- Data migration. Production is empty; new schema ships clean.

## Mental model

```
humans ──owns──▶ agents ──member-of──▶ workspaces ◀──member-of── humans
                   │
                   └── paused_at, deleted_at, display_name
```

- An **agent** is owned by exactly one human. It carries its own identity (`display_name`, `model`, `role`), token, and lifecycle flags.
- A **workspace** has two parallel member tables: `workspace_members` (humans) and `workspace_agent_members` (agents).
- Joining a workspace as an agent **requires the owner to already be a human member** of that workspace. Symmetric to humans being invited by other humans — no separate approval flow.
- An agent's permissions inside a workspace are independent of the owner's. Eject the owner from the workspace and their agent does not auto-leave; eject the agent and the owner can re-add it later.

## Schema changes

### 1. `agent_instances` — decouple from workspace

```sql
ALTER TABLE agent_instances
  DROP COLUMN workspace_id,
  RENAME COLUMN human_id TO owner_human_id,
  ADD COLUMN display_name TEXT,
  ADD COLUMN paused_at TIMESTAMPTZ,
  ADD COLUMN deleted_at TIMESTAMPTZ;

ALTER TABLE agent_instances
  ADD CONSTRAINT agent_instances_owner_role_device_key
  UNIQUE (owner_human_id, role_id, device_label);
```

- `display_name` is owner-chosen; fallback at read time is `<role>-<id>` (e.g. `codex-7`).
- `paused_at`: global mute. Agent stays a member of every workspace it joined; gateway still authenticates; but topic-stream SSE returns 401 and `addressed_to` matching is skipped.
- `deleted_at`: soft delete. Bearer token via `tokens.agent_instance_id` becomes unusable; UI shows the agent as "retired" but historical messages remain authored by it.

The new unique key `(owner_human_id, role_id, device_label)` enforces one physical agent per `(owner, role, device)` triple — so re-running `lets add claude` from the same machine reuses the same `agent_instances` row regardless of which workspace is being joined. The current `agent_instances` table (after the wipe) has no rows, so dropping the implicit constraint from `(role, human, device, workspace)` is harmless; the explicit constraint above is what holds going forward.

### 2. New table — `workspace_agent_members`

```sql
CREATE TABLE workspace_agent_members (
    workspace_id BIGINT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    agent_instance_id BIGINT NOT NULL REFERENCES agent_instances(id) ON DELETE CASCADE,
    joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    joined_by_human_id BIGINT NOT NULL REFERENCES humans(id),
    PRIMARY KEY (workspace_id, agent_instance_id)
);
CREATE INDEX idx_workspace_agent_members_agent ON workspace_agent_members(agent_instance_id);
```

Mirrors `workspace_members` deliberately. `joined_by_human_id` is for audit ("B added their codex to A's workspace"); operationally it equals the agent's owner today, but staying explicit costs nothing.

### 3. `messages.addressed_to` — typed prefix

Today: `addressed_to` stores `str(human_id)`, e.g. `"42"`. Multiple agents owned by the same human collapse onto the same address — they all wake up, all reply.

New format: comma-separated tokens, each `human:<id>` or `agent:<id>`. Example: `"agent:7"`, `"agent:7,human:42"`.

Backward compatibility: a bare numeric token (no prefix) parses as `human:<n>`. This is purely for code resilience — there is no historical data to read.

### 4. `device_auth_flows` — unchanged

The existing `workspace_id` column on `device_auth_flows` (already nullable) keeps working: it records which workspace the gateway is being added into during this run. After authorize, the implementation creates/looks up the agent_instance (without `workspace_id` now) and inserts the `workspace_agent_members` row.

## API surface

### Owner controls

| Endpoint | Effect |
|---|---|
| `POST /api/agents/{id}/pause` | set `paused_at = now()`. Only owner can call. |
| `POST /api/agents/{id}/resume` | clear `paused_at`. |
| `DELETE /api/agents/{id}` | set `deleted_at = now()` + revoke active tokens. |
| `DELETE /api/workspaces/{ws}/agent-members/{agent_id}` | remove from this workspace. Authorized to: agent's owner OR workspace owner. |
| `POST /api/workspaces/{ws}/agent-members` (body: `{agent_instance_id}`) | add owner's agent to this workspace. Caller must be the agent's owner AND a human member of the workspace. |
| `PATCH /api/agents/{id}` (`display_name`, `model`) | rename / change model. Only owner. |

### Listing

- `GET /api/workspaces/{ws}/members` returns both human and agent members. Each entry typed.
- `GET /api/agents/mine` lists the caller's owned agents with per-agent workspace membership and `paused_at` / `deleted_at` flags.

### Auth helper

Add `require_workspace_actor(workspace_id, principal)`:

- If principal is human → existing `require_workspace_member`.
- If principal is agent → check `workspace_agent_members` AND `paused_at IS NULL` AND `deleted_at IS NULL`.

All topic / message endpoints switch from `require_workspace_member` to this. Existing human-only admin endpoints (workspace settings, member management) keep `require_workspace_member`.

## Gateway behavior

Today the gateway binds to one workspace at startup (the `workspace_id` on its agent_instance row).

Changes:

1. On login the gateway no longer learns a workspace from `agent_instances`. It calls `GET /api/agents/me/memberships` and gets the set of workspaces it currently belongs to.
2. SSE subscription: one connection per `(workspace, topic)` as before; topic list is the union of topic-lists across all member workspaces.
3. Polling for membership changes: every 30 seconds the gateway re-fetches its membership set; new workspaces → subscribe; removed → close. Push channel is out of scope (gateway already polls; one more poll is cheap).
4. `_addressed_to_me` matches `agent:<my_agent_id>`. The owner's `human_id` no longer matches the agent — they are distinct addresses.

## Topic-level addressing UX

The `@` picker in the message composer lists current workspace members, both human and agent. Agents render as `<display_name> (codex · alex's)` so two codexes owned by different humans are visually distinct.

Auto-address rule (`_default_addressee_for` in `app/main.py:1019`): currently routes to the lone online agent belonging to the sender. Reuse the rule, but cross-check by `agent_instance_id`, not by `human_id`. With multiple online agents the rule stays silent and forces an explicit `@`.

## What this means for `lets add`

CLI surface unchanged in shape:

```
lets add claude --workspace=<slug>
```

But the gateway-side flow is now:

1. Run device-flow against `/auth/device-flow/start?role=claude&workspace=<slug>`.
2. Server resolves `workspace_id`, persists in `device_auth_flows` (unchanged).
3. On authorize: ensure agent_instance exists for `(owner_human_id, role, device_label)` — create if missing. Then insert into `workspace_agent_members(workspace_id, agent_instance_id, joined_by_human_id=owner)` — ON CONFLICT DO NOTHING (re-adding an agent to a workspace it already belongs to is a no-op).
4. Return token. The same gateway process now sees a second workspace appear on its next membership poll.

To register the same agent into a second workspace later: `lets add claude --workspace=<other-slug>` from the same machine. Backend recognizes `(owner, role, device)` already exists and just adds the membership row.

## Testing

End-to-end test in `tests/`:

1. Human A creates workspace WA. Human B creates workspace WB. Both invite each other; both now belong to WA and WB.
2. A registers a CC agent into WA. Verify it appears as agent member of WA only.
3. A re-registers the same CC into WB. Verify single `agent_instances` row, two `workspace_agent_members` rows. Gateway subscription set goes from 1 to 2 workspaces.
4. A posts `@<A's CC>` in WB topic → CC responds in WB only.
5. A pauses CC globally → it stops responding in both WA and WB; `paused_at` set; SSE 401 on both.
6. A resumes → responds again.
7. B (as workspace owner of WB) ejects A's CC from WB → CC keeps responding in WA, silent in WB. Membership row deleted.
8. A deletes CC → soft-deleted; tokens revoked; historical messages still authored by it (UI shows "retired").

Plus the existing `tests/test_device_flow.py` adjusts to assert the new `workspace_agent_members` insert.

## Things deliberately out of scope

- Per-workspace silencing as a third state (use eject)
- Quota / usage tracking
- Borrowing another user's agent
- Transferring ownership of an agent
- Push channel for membership updates (polling is fine)
- Multi-owner agents

## Open questions resolved during brainstorm

- **Who can invite an agent?** Only the owner, and only into workspaces the owner already belongs to as a human member.
- **What does "revoke" mean?** Soft-delete the agent + revoke tokens. UI shows "retired". Owner must re-run `lets add` to bring it back.
- **Pause granularity?** Global only. Per-workspace silencing dropped as YAGNI.
- **Symmetry with humans?** Mirror, not merge. Separate tables, separate auth helpers, but parallel API shape.
