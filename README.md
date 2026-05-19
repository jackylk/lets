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

## v1.5 Artifact Substrate (Track D)

Artifacts are the structured products of collaboration (PPTs / docs / code /
analyses). Each artifact has a stable identity, a version chain, and a backend
adapter that knows how to read / write / diff / list versions.

### Schema (added by Track D)

- `artifacts` (id, slug, type, backend, backend_ref, title, topic_id, current_version_id, ...)
- `artifact_versions` (id, artifact_id, version_label, backend_revision_id, summary, preview_uri, created_by_*)

### Backend supported in v1.5b

- `git` — files live in a git repo pointed to by `LETS_GIT_REPO` env var

Future backends (v1.5c+): `google-slides`, `google-docs`, `google-sheets`,
`object-storage`, `feishu-*`. See `docs/artifact-sync-strategy.md`.

### API

```text
POST   /api/artifacts                 # create (initial version v0)
POST   /api/artifacts/{id}/update     # add a new version with semantic label
GET    /api/artifacts/{id}            # read current (or ?version_label=v1)
GET    /api/artifacts/{id}/versions   # list version chain
GET    /api/artifacts/{id}/diff       # ?from_label=v0&to_label=v1
```

All require `Authorization: Bearer lets_...` (see Track B docs).

### Setup

```bash
mkdir -p ~/lets-artifacts && cd ~/lets-artifacts && git init && \
  git commit --allow-empty -m init
export LETS_GIT_REPO=~/lets-artifacts
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## v1.5 Deploy (Track B)

### Local dev

```bash
# One-time: initialize the artifacts git repo (Track D needs this)
mkdir -p ~/lets-artifacts && cd ~/lets-artifacts && git init && \
  git commit --allow-empty -m "init"
cd -

# Run the backend
export LETS_GIT_REPO=~/lets-artifacts
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Verify it's up:
```bash
curl http://127.0.0.1:8000/api/context
# {"project":{"name":"Lets",...}}
```

### Container

```bash
docker compose up -d
curl http://127.0.0.1:8000/api/context
```

The DB persists in the named volume `lets-data`. To enable Track D artifact endpoints in the container, mount an artifacts git repo and set `LETS_GIT_REPO` (see `docker-compose.yml` comments).

### Issue a token for a remote agent

```bash
.venv/bin/python -m app.tokens_cli issue --human Neo --role claude --device neo-mbp --label work-laptop
```

The CLI prints the plaintext token once (the server stores only a SHA256 hash; the plaintext cannot be recovered). Paste it into the remote agent's `.mcp.json`:

```json
{
  "mcpServers": {
    "lets": {
      "type": "http",
      "url": "https://your-lets-host/mcp/",
      "headers": { "Authorization": "Bearer lets_..." }
    }
  }
}
```

Manage tokens:

```bash
.venv/bin/python -m app.tokens_cli list --human Neo
.venv/bin/python -m app.tokens_cli revoke --id 5
```

### Public endpoints (no auth)

`GET /` · `GET /mock` · `GET /api/context` · `GET /api/identity/me`

### Auth-required endpoints

All other `/api/...` routes and the `/mcp/` MCP endpoint require `Authorization: Bearer lets_...`. Without it: `401 missing or invalid token`.
