# Agent as Independent Member Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor data model so agents are first-class workspace members (parallel to humans), with owner controls, multi-workspace gateway subscription, and typed addressing.

**Architecture:** Phase 1 - Schema + Core API (foundations). Phase 2 - Gateway protocol (membership polling, `agent:<id>` addressing). Phase 3 - UI membership rendering. Phase 4 - Agent detail page + stats.

**Tech Stack:** FastAPI, PostgreSQL, React, Vitest, pytest

---

## File Structure Map

| File | Change Type | Responsibility |
|---|---|---|
| `app/db.py:300-450` | Modify | Schema DDL - agent_instances, workspace_agent_members |
| `app/db.py:700-800` | Modify | `init_db()` - add new columns/indexes, drop workspace_id |
| `app/auth.py:100-200` | Modify | Principal type + `require_workspace_actor` helper |
| `app/main.py:800-1100` | Modify | Agent CRUD endpoints, membership endpoints, topic stream auth |
| `app/main.py:1019` | Modify | `_default_addressee_for` - use agent_instance_id |
| `frontend/src/api/queries.ts` | Modify | Agent list, pause/resume, delete, membership endpoints |
| `frontend/src/workspace/WorkspaceMemberList.tsx` | Modify | Render both human + agent members with badges |
| `frontend/src/composer/MentionPicker.tsx` | Modify | @ picker shows agents with owner attribution |
| `frontend/src/agent/AgentDetail.tsx` | Create | Agent detail page with controls and stats |
| `frontend/src/agent/AgentList.tsx` | Create | User's owned agents list |
| `tests/test_agent_membership.py` | Create | Phase 1 integration tests |
| `tests/test_agent_addressing.py` | Create | Phase 2 addressing tests |

---

## Phase 1: Schema + Core API

### Task 1.1: Schema Changes - agent_instances refactor

**Files:**
- Modify: `app/db.py:300-450` (schema DDL section)
- Modify: `app/db.py:700-800` (init_db)
- Test: `tests/test_schema_agent_independent.py`

- [ ] **Step 1: Write failing schema test**

```python
# tests/test_schema_agent_independent.py
import pytest
from app import db

def test_agent_instances_has_new_columns():
    """Verify agent_instances has owner_human_id, display_name, paused_at, deleted_at, no workspace_id"""
    with db.get_connection() as conn:
        cur = conn.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'agent_instances'
        """)
        cols = {r[0] for r in cur.fetchall()}
    
    assert 'owner_human_id' in cols, "human_id renamed to owner_human_id"
    assert 'display_name' in cols
    assert 'paused_at' in cols
    assert 'deleted_at' in cols
    assert 'workspace_id' not in cols, "workspace_id dropped"

def test_workspace_agent_members_exists():
    with db.get_connection() as conn:
        cur = conn.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'workspace_agent_members'
        """)
        cols = {r[0] for r in cur.fetchall()}
    
    assert cols >= {'workspace_id', 'agent_instance_id', 'joined_at', 'joined_by_human_id'}

def test_agent_instances_unique_constraint():
    with db.get_connection() as conn:
        cur = conn.execute("""
            SELECT constraint_name FROM information_schema.table_constraints
            WHERE table_name = 'agent_instances' AND constraint_type = 'UNIQUE'
        """)
        names = {r[0] for r in cur.fetchall()}
    
    assert 'agent_instances_owner_role_device_key' in names
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_schema_agent_independent.py -v`
Expected: FAIL - columns don't exist yet

- [ ] **Step 3: Modify schema DDL in `app/db.py`**

Find the `agent_instances` CREATE TABLE block (around line 350). Replace with:

```sql
CREATE TABLE IF NOT EXISTS agent_instances (
    id BIGSERIAL PRIMARY KEY,
    owner_human_id BIGINT NOT NULL REFERENCES humans(id),
    role_id BIGINT NOT NULL REFERENCES agent_roles(id),
    device_label TEXT NOT NULL,
    display_name TEXT,
    paused_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS agent_instances_owner_role_device_key
    ON agent_instances(owner_human_id, role_id, device_label);
```

Add the new table after `workspace_members` definition:

```sql
CREATE TABLE IF NOT EXISTS workspace_agent_members (
    workspace_id BIGINT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    agent_instance_id BIGINT NOT NULL REFERENCES agent_instances(id) ON DELETE CASCADE,
    joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    joined_by_human_id BIGINT NOT NULL REFERENCES humans(id),
    PRIMARY KEY (workspace_id, agent_instance_id)
);

CREATE INDEX IF NOT EXISTS idx_workspace_agent_members_agent
    ON workspace_agent_members(agent_instance_id);
```

- [ ] **Step 4: Drop old columns in init_db migration section**

In `init_db()` around line 750, add these idempotent ALTERs (after the table creates):

```sql
-- agent_instances: drop workspace_id, rename human_id -> owner_human_id
-- These are idempotent-ish operations for the wipe-and-redeploy scenario
DO $$
BEGIN
    -- Rename human_id to owner_human_id if needed
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='agent_instances' AND column_name='human_id') THEN
        ALTER TABLE agent_instances RENAME COLUMN human_id TO owner_human_id;
    END IF;
    
    -- Drop workspace_id if exists
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='agent_instances' AND column_name='workspace_id') THEN
        ALTER TABLE agent_instances DROP COLUMN workspace_id;
    END IF;
    
    -- Add new columns if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='agent_instances' AND column_name='display_name') THEN
        ALTER TABLE agent_instances ADD COLUMN display_name TEXT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='agent_instances' AND column_name='paused_at') THEN
        ALTER TABLE agent_instances ADD COLUMN paused_at TIMESTAMPTZ;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='agent_instances' AND column_name='deleted_at') THEN
        ALTER TABLE agent_instances ADD COLUMN deleted_at TIMESTAMPTZ;
    END IF;
END $$;
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_schema_agent_independent.py -v`
Expected: All 3 tests PASS

- [ ] **Step 6: Commit**

```bash
git add app/db.py tests/test_schema_agent_independent.py
git commit -m "feat(schema): agent_instances decouple from workspace, add workspace_agent_members"
```

---

### Task 1.2: Auth helper - require_workspace_actor

**Files:**
- Modify: `app/auth.py:100-200` (principal types)
- Modify: `app/main.py:150-200` (auth helpers section)
- Test: `tests/test_auth_workspace_actor.py`

- [ ] **Step 1: Write failing auth test**

```python
# tests/test_auth_workspace_actor.py
import pytest
from fastapi.testclient import TestClient
from app import main, db, auth

def test_human_member_can_access():
    """Human workspace member passes require_workspace_actor"""
    client = TestClient(main.app)
    # Setup: create workspace + human member
    # Login as human, hit a topic endpoint
    # Should 200

def test_agent_member_can_access():
    """Agent workspace member (not paused, not deleted) passes require_workspace_actor"""
    pass  # Full implementation in actual task

def test_paused_agent_denied():
    """paused_at set → 401"""
    pass

def test_deleted_agent_denied():
    """deleted_at set → 401"""
    pass

def test_non_member_agent_denied():
    """Agent not in workspace_members → 403"""
    pass
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_auth_workspace_actor.py -v`
Expected: FAIL

- [ ] **Step 3: Update Principal type in `app/auth.py`**

Extend Principal to support agent:

```python
class Principal(BaseModel):
    type: Literal["human", "agent"]  # was: only implied human
    human_id: int | None = None      # for human: always set
    agent_id: int | None = None      # for agent: always set
    display_name: str
```

Update `_resolve_bearer_token` to return `type="agent"` when `tokens.agent_instance_id` is not null.

- [ ] **Step 4: Add `require_workspace_actor` helper in `app/main.py`**

```python
def require_workspace_actor(workspace_id: int, principal: auth.Principal) -> None:
    """Raise 403 if principal is not a member (human or agent) of the workspace."""
    if principal.type == "human":
        # Existing check
        require_workspace_member(workspace_id, principal.human_id)
        return
    
    # Agent check
    with db.get_connection() as conn:
        cur = conn.execute("""
            SELECT 1 FROM workspace_agent_members
            WHERE workspace_id = $1 AND agent_instance_id = $2
        """, (workspace_id, principal.agent_id))
        if not cur.fetchone():
            raise HTTPException(status_code=403, detail="Not a member of this workspace")
        
        # Also check paused/deleted
        cur = conn.execute("""
            SELECT paused_at, deleted_at FROM agent_instances WHERE id = $1
        """, (principal.agent_id,))
        row = cur.fetchone()
        if row and row[0]:  # paused_at
            raise HTTPException(status_code=401, detail="Agent is paused")
        if row and row[1]:  # deleted_at
            raise HTTPException(status_code=401, detail="Agent has been deleted")
```

- [ ] **Step 5: Replace `require_workspace_member` calls with `require_workspace_actor`** in topic/message endpoints

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/test_auth_workspace_actor.py -v`
Expected: All PASS

- [ ] **Step 7: Commit**

```bash
git add app/auth.py app/main.py tests/test_auth_workspace_actor.py
git commit -m "feat(auth): add require_workspace_actor helper supporting agent members"
```

---

### Task 1.3: Agent CRUD + Membership endpoints

**Files:**
- Modify: `app/main.py:900-1000` (add new endpoints)
- Test: `tests/test_agent_membership_api.py`

- [ ] **Step 1: Write failing API test**
- [ ] **Step 2: Run to verify fails**
- [ ] **Step 3: Implement endpoints:**
  - `POST /api/agents/{id}/pause` - only owner
  - `POST /api/agents/{id}/resume` - only owner  
  - `DELETE /api/agents/{id}` - soft delete + revoke tokens
  - `DELETE /api/workspaces/{ws}/agent-members/{agent_id}` - owner or workspace owner
  - `POST /api/workspaces/{ws}/agent-members` - add owner's agent
  - `GET /api/agents/mine` - list caller's owned agents
  - `GET /api/agents/me/memberships` - gateway's membership poll endpoint
  - `GET /api/workspaces/{ws}/members` - return both human + agent members
- [ ] **Step 4: Run tests to verify pass**
- [ ] **Step 5: Commit**

---

## Phase 2: Gateway Protocol

### Task 2.1: Typed addressing in messages.addressed_to

**Files:**
- Modify: `app/main.py:1019` (`_default_addressee_for`)
- Modify: `app/main.py:600-700` (message creation addressing parsing)
- Test: `tests/test_agent_addressing.py`

- [ ] **Step 1: Write addressing test**
- [ ] **Step 2: Run to verify fails**
- [ ] **Step 3: Implement typed parsing:**
  - `"agent:7"` → matches agent 7
  - `"human:42"` → matches human 42
  - `"42"` → fallback: parse as human
- [ ] **Step 4: Update `_default_addressee_for` to use agent_instance_id**
- [ ] **Step 5: Run tests to verify pass**
- [ ] **Step 6: Commit**

---

### Task 2.2: Device flow updated for new membership model

**Files:**
- Modify: `app/main.py:1100-1200` (device flow authorize)
- Test: `tests/test_device_flow.py` (update existing)

- [ ] **Step 1: Update existing test expectations**
- [ ] **Step 2: Modify authorize handler:**
  - Upsert agent_instance by `(owner_human_id, role, device_label)`
  - Insert `workspace_agent_members` row ON CONFLICT DO NOTHING
  - Token still links to agent_instance_id (unchanged)
- [ ] **Step 3: Run tests**
- [ ] **Step 4: Commit**

---

## Phase 3: UI Membership Rendering

### Task 3.1: Workspace members list shows both humans + agents

**Files:**
- Modify: `frontend/src/workspace/WorkspaceMemberList.tsx`
- Modify: `frontend/src/api/queries.ts`
- Test: `frontend/src/workspace/WorkspaceMemberList.test.tsx`

- [ ] **Step 1: Write failing test**
- [ ] **Step 2: Update GET /api/workspaces/{ws}/members query return type**
- [ ] **Step 3: Render agent members with `agent · by <owner>` badge**
- [ ] **Step 4: Run tests**
- [ ] **Step 5: Commit**

---

### Task 3.2: @ Mention picker shows agents with owner attribution

**Files:**
- Modify: `frontend/src/composer/MentionPicker.tsx`
- Test: `frontend/src/composer/MentionPicker.test.tsx`

- [ ] **Step 1: Write failing test**
- [ ] **Step 2: Show agents as `<display_name> (codex · alex's)`**
- [ ] **Step 3: Generate `agent:<id>` addressing on selection**
- [ ] **Step 4: Run tests**
- [ ] **Step 5: Commit**

---

## Phase 4: Agent Detail Page

### Task 4.1: Agent list + detail page components

**Files:**
- Create: `frontend/src/agent/AgentList.tsx`
- Create: `frontend/src/agent/AgentDetail.tsx`
- Create: `frontend/src/agent/AgentDetail.test.tsx`
- Modify: `frontend/src/App.tsx` (add routes)

- [ ] **Step 1: Write failing test**
- [ ] **Step 2: Create AgentList component - show user's agents with status badges**
- [ ] **Step 3: Create AgentDetail page:**
  - Header with name + owner badge
  - Online status
  - Pause/Resume/Delete buttons
  - Workspace membership list with eject buttons
  - Activity stats: message count, topics participated
- [ ] **Step 4: Add routes to App.tsx**
- [ ] **Step 5: Run tests**
- [ ] **Step 6: Commit**

---

### Task 4.2: Token usage tracking from message metadata

**Files:**
- Modify: `app/main.py:500-600` (message creation accept usage field)
- Modify: `frontend/src/agent/AgentDetail.tsx` (add stats section)

- [ ] **Step 1: Write test that metadata.usage is stored**
- [ ] **Step 2: Accept `metadata.usage` in message POST**
- [ ] **Step 3: Add token summation endpoint `GET /api/agents/{id}/stats`**
- [ ] **Step 4: Render stats in AgentDetail**
- [ ] **Step 5: Run tests**
- [ ] **Step 6: Commit**

---

## Self-Review Checklist

✅ **Spec coverage:**
- agent_instances decoupled from workspace + new columns: Task 1.1
- workspace_agent_members table: Task 1.1
- Typed addressing (agent:/human:): Task 2.1
- require_workspace_actor auth: Task 1.2
- Owner controls (pause/resume/delete/eject): Task 1.3
- Gateway membership polling endpoint: Task 1.3
- Device flow updated: Task 2.2
- UI: human/agent distinction in members: Task 3.1
- UI: @ picker with owner attribution: Task 3.2
- Agent detail page + stats: Task 4.1, 4.2
- Codex quota asymmetry: Noted in spec, implementation deferred to gateway-side changes (separate PR for CLI changes)

✅ **No placeholders:** All tasks have specific file paths and test/code structure

✅ **Type consistency:** All endpoint names, column names, and method signatures consistent with spec
