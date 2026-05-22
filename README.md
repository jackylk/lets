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
| `agent_types` | Known agent types, seeded with `claude` and `codex` |
| `agent_instances` | `(agent_type, human, device)` tuples — a human can run multiple agents across devices |
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

## v1.5 Project Lifecycle (Track C1, local mode)

Projects are the top-level container for collaborative work. In v1.5b's local mode,
a project is just a slug + name + optional local `repo_path`. GitHub OAuth and
multi-user invite land in Track C2.

### Schema (added by Track C1)

- `projects` (id, slug, name, description, owner_human_id, repo_path, ...)
- `topics.project_id` (FK to projects; old topics auto-assigned to a `default` project on migration)
- `messages.type` CHECK widened to include `project_proposal` (idempotent rebuild migration)

### API

```text
POST   /api/projects                       # create
GET    /api/projects                       # list
GET    /api/projects/{id}                  # read
PATCH  /api/projects/{id}                  # update name / description / repo_path
POST   /api/projects/{id}/topics           # create a topic in the project
GET    /api/projects/{id}/topics           # list topics in the project
GET    /api/topics/{id}                    # read a topic
GET    /api/projects/{id}/spec             # read-only spec view (CLAUDE.md / .mcp.json / .claude/**)
                                           # ?include_content=true to also return base64 content
```

All require `Authorization: Bearer lets_...`.

### Quick start

```bash
# Create a project pointing at an existing local repo
TOKEN=$(.venv/bin/python -m app.tokens_cli issue --human admin --label local 2>/dev/null | head -1)
curl -X POST http://127.0.0.1:8000/api/projects \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Q3 Review","repo_path":"/Users/me/work/q3-review"}'
# {"id":2,"slug":"q3-review","name":"Q3 Review",...}

# List spec files
curl http://127.0.0.1:8000/api/projects/2/spec -H "Authorization: Bearer $TOKEN"
```

See `docs/agent-spec-collaboration.md` for the `project_proposal` typed message
convention used by the Web UI / agents when suggesting new projects.

## v1.5 Web-UI Backend Glue (Track C1.5)

New endpoints / capability added to support the Track F React frontend without
forcing it to fall back to polling or in-memory state. All require Bearer auth.

| Endpoint | Purpose |
|---|---|
| `GET  /api/topics/{id}/messages?after_id=N` | Incremental fetch (poll fallback for SSE reconnect) |
| `GET  /api/topics/{id}/stream` | SSE live updates (single-process in-memory broadcaster) |
| `GET  /api/attention?human_id=N` | Cross-topic queue: `needs_decision` / `mentioned_questions` / `suggestions` |
| `GET  /api/artifacts?topic_id=N` | List artifacts in a topic |
| `GET  /api/topics/{id}/participants` | Humans + agents who've posted in a topic |
| `GET  /api/projects/{id}/git-status` | HEAD commit + dirty file list (read-only `git log -1` + `git status --short`) |
| `POST /api/projects/{id}/spec/apply` | Atomic write-back for `CLAUDE.md` / `.mcp.json` / `.claude/**` |
| `GET  /api/agents/online` | Agent instances whose Bearer token was used in the last 5 min |
| `/app` (static mount) | Serves built frontend when `LETS_FRONTEND_DIST=/abs/path/to/frontend/dist` is set |

New typed messages added by Track C1.5:
- `goal_proposal` — used by the Goal Card flow above the topic stream

### SSE limitations (v1.5b)

The SSE broadcaster keeps its subscriber list in **process memory**. Single Railway
replica works; horizontally scaling means a publish on replica A doesn't reach a
subscriber on replica B. The multi-replica path (Postgres `LISTEN/NOTIFY` or
Redis pub/sub) is documented as Track I in `docs/superpowers/plans/RAILWAY.md`.

### Quick dev: open the built SPA against this backend

```bash
cd frontend && pnpm install && pnpm build
cd ..
LETS_FRONTEND_DIST=$(pwd)/frontend/dist .venv/bin/uvicorn app.main:app --reload
# Open http://127.0.0.1:8000/app/
```

### Full local dogfood while Railway is unavailable

Use the local FastAPI site as the product surface:

```bash
./scripts/dev-local.sh
```

Then open the printed dev login URL:

```text
http://127.0.0.1:8000/auth/dev/login?human=<you>
```

That sets the same `lets_session` browser cookie shape as GitHub OAuth, but
only when `LETS_DEV_SESSIONS=1` is enabled by the script. After the local
website is open, register this computer the Railway-style way:

```bash
LETS_HOST=http://127.0.0.1:8000 .venv/bin/python -m app.gateway login
LETS_HOST=http://127.0.0.1:8000 .venv/bin/python -m app.gateway run
```

`gateway login` opens the local browser authorization page, reuses the browser
session, then saves the token into `~/.lets/token`.

## Track F: Web Frontend

The React SPA lives under `frontend/`.

```bash
cd frontend && pnpm install
cd frontend && pnpm dev    # fixture mode, http://localhost:5173
cd frontend && pnpm build  # builds into frontend/dist for production serving
```

Production: `uvicorn app.main:app` then `http://localhost:8000/app`. The backend
serves the SPA from `frontend/dist` if it exists (no env var required;
`LETS_FRONTEND_DIST` still works as an explicit override).

### v1.5 — GitHub OAuth

Register an OAuth App at https://github.com/settings/applications/new with:
- Homepage URL: `https://<your-domain>`
- Authorization callback URL: `https://<your-domain>/auth/github/callback`

Set on the server:
- `GITHUB_CLIENT_ID=...`
- `GITHUB_CLIENT_SECRET=...`
- `GITHUB_REDIRECT_URI=https://<your-domain>/auth/github/callback`
- `LETS_COOKIE_SECURE=true` (set to `false` for local http)

After successful OAuth, the backend sets an opaque `lets_session` cookie
(HttpOnly, SameSite=Lax). The SPA reads `/auth/me` to detect the logged-in
human; agent CLI tokens (Bearer in `.mcp.json`) remain a separate credential
class for `/mcp` and Track A API access.
