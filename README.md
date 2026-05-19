# Lets

Minimal local collaboration board for one human and multiple local coding
agents.

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then open `http://127.0.0.1:8000`.

For local MCP dogfooding, replace `lets_REPLACE_WITH_LOCAL_TOKEN` in
`.mcp.json` with a token from:

```bash
.venv/bin/python -m app.tokens_cli issue --human admin --label local-dev
```

## Core Flow

1. Create an idea or task in the web UI.
2. Let an agent list work items.
3. The agent claims one item.
4. Agents report status and findings.
5. The web UI shows shared progress.

## Agent API

The first version exposes both HTTP endpoints and a local MCP server.

### HTTP

```text
GET  /api/context
GET  /api/work-items
POST /api/work-items/{id}/claim
DELETE /api/work-items/{id}
POST /api/status
POST /api/findings
GET  /api/activity
```

### MCP

Run:

```bash
python -m app.mcp_server
```

Tools:

```text
get_project_context
list_work_items
claim_work_item
report_status
publish_finding
list_peer_activity
```

## v1.5 Schema (Track A)

The v1 tables (`work_items`, `agents`, `status_updates`, `findings`, `human_notes`) stay in place for backward compatibility. Track A adds six new tables and a unified typed message stream:

| Table | Purpose |
|-------|---------|
| `humans` | Typed human identity (name UNIQUE, optional email) |
| `agent_roles` | Known agent roles, seeded with `claude` and `codex` |
| `agent_instances` | `(role, human, device)` tuples — a human can run multiple agents across devices |
| `events` | Append-only event log (must-source set: idea.claimed / finding.promoted / decision.created / work_session.* / metric_run.completed / state_branch.*) |
| `topics` | Minimal topic table (extended later in Track C) |
| `messages` | Unified typed stream — **new canonical surface** for conversation, status, findings, decisions, etc. |

### Typed messages (13 variants)

`chat` · `status` · `finding` · `decision` · `question` · `handoff` · `review` · `artifact_revision` · `spec_change` · `nudge` · `proactive_finding` · `task_tree_proposal` · `system`

### New endpoints

```text
GET  /api/identity/me           # headers: X-Lets-Human (required), X-Lets-Human-Email, X-Lets-Agent-Role, X-Lets-Device
POST /api/events                # append a typed event
GET  /api/events                # filter by target_type / target_id / topic_id / event_type
POST /api/messages              # post a typed message into a topic
GET  /api/topics/{id}/messages  # topic stream, optional ?type= filter (repeatable)
```

### Legacy mirroring

Existing endpoints (`POST /api/status`, `POST /api/findings`, `POST /api/feedback`) now also mirror to `messages` when an optional `topic_id` is passed. Old call sites without `topic_id` keep working unchanged.

### Test harness

```bash
.venv/bin/pytest -v
```

49 tests, full suite green. End-to-end PPT scenario at `tests/test_e2e_ppt_scenario.py` stitches identity + events + messages through HTTP to verify the substrate.
