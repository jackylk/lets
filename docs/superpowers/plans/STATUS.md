# Lets v1.5 Delivery Status

> **Snapshot at 2026-05-19 (refresh after Track F)** —— v1.5a + v1.5b + 本地 dogfood **全栈**已交付，**182 backend tests + 52 frontend tests + 3 Playwright E2E passing**。Track F 在 `track-f-web-frontend` 分支（24 commit ahead of main），等 PR merge。下一步：Railway 部署，按 α 路径（SQLite + Railway Volume，单 replica）— Track G/H/I 真有压力时再做。
>
> Track F 期间换了协作约定：CC（前端）在 `track-f-web-frontend` 分支跑，并行 Codex（后端 C1/C1.5）继续在 `main` 上推。两边代码无冲突，merge 时按 `--no-ff` 保留交错时序。

---

## 1. v1.5a + 1.5b + 本地 dogfood 全景

| Track | Plan | Tasks | Status |
|-------|------|:-----:|:------:|
| **A. Schema Substrate** | `2026-05-19-track-a-schema-substrate.md` | 15 / 15 | ✅ |
| **B. Network Transport** | `2026-05-19-track-b-network-transport.md` | 12 / 12 | ✅ |
| **D. Artifact Substrate** | `2026-05-19-track-d-artifact-substrate.md` | 13 / 13 | ✅ |
| **C1. Local Project Lifecycle** | `2026-05-19-track-c1-local-projects.md` | 10 / 10 | ✅ |
| **C1.5. Web-UI Backend Glue** | `2026-05-19-track-c1.5-webui-backend-glue.md` | 7 / 7 (+ T8 文档) | ✅ |
| **F. Web Frontend** | `2026-05-19-track-f-web-frontend.md` | 46 / 46 | ✅ |
| **G/H/I. Railway** | `RAILWAY.md` | 未启动 | 📦 backlog（v1.5a 起步走 α 路径，单 replica + SQLite + Volume）|
| **总计 (已交付)** | | **103 / 103** | ✅ |

测试: 182 backend pytest + 52 frontend vitest + 3 Playwright E2E（1 skipped 是 real-mode 手动场景），0 failed. C1 端到端 demo: `tests/test_e2e_project_lifecycle.py`. Track A 原 PPT 场景仍跑: `tests/test_e2e_ppt_scenario.py`. Track F PPT 场景 Playwright: `frontend/e2e/ppt-scenario.spec.ts`.

### Track C1 / C1.5 增量速览

- **C1**: projects 表 + topics.project_id FK + 8 个 endpoint (POST/GET/PATCH /api/projects, POST/GET /api/projects/{id}/topics, GET /api/topics/{id}, GET /api/projects/{id}/spec)。同时补了 Track A plan 误以为已有但实际没有的 `project_proposal` typed message (idempotent CHECK rebuild)。
- **C1.5**: SSE broadcaster (`/api/topics/{id}/stream`) + `?after_id=` 增量 + 跨 topic 聚合 (`/api/attention`) + context pane 三个端点 (artifacts-by-topic / participants / git-status) + `goal_proposal` typed message + spec write-back (`/api/projects/{id}/spec/apply`) + agents-online (`/api/agents/online` 基于 token.last_used_at) + SPA 静态挂载 (`/app` via `LETS_FRONTEND_DIST`)。新增 `messages.addressed_to` 列 + `addressed_to`-aware CHECK rebuild。

---

## 2. 实际交付清单（按能力分）

### Schema (Track A)

| 表 | 用途 |
|----|------|
| `humans` | typed human 身份 (`name UNIQUE`, optional email) |
| `agent_roles` | 已知 agent 角色（seeded `claude`, `codex`）|
| `agent_instances` | (role_id, human_id, device_label) UNIQUE composite |
| `events` | append-only 事件流 |
| `topics` | 最小 topic 实体（Track C 会扩展）|
| `messages` | 统一 13 种 typed message（chat/status/finding/decision/question/handoff/review/artifact_revision/spec_change/nudge/proactive_finding/task_tree_proposal/system）|

v1 老表（`work_items`/`agents`/`status_updates`/`findings`/`human_notes`）保留为 backward compat。`status/findings/feedback` 三个 POST 在传 `topic_id` 时也会 mirror 一份到 `messages`。

### Auth + Network (Track B)

| 能力 | 实现 |
|------|------|
| `tokens` 表 + SHA256 hash 存储（plaintext 不可恢复）| `app/auth.py` |
| Bearer token dependency | `get_current_principal` FastAPI dep |
| 颁发 / 列表 / 撤销 CLI | `python -m app.tokens_cli {issue,list,revoke}` |
| 保护的 endpoint | `/api/messages`, `/api/events`, `/api/artifacts*`, `/mcp/` |
| 公开 endpoint | `/`, `/mock`, `/api/context`, `/api/identity/me` |
| MCP streamable-http transport | FastMCP `streamable_http_app()` mount 到 `/mcp/` + ASGI Bearer middleware |
| Container deploy | `Dockerfile` (python:3.13-slim + git) + `docker-compose.yml` + `LETS_DB_PATH` env |

### Artifact (Track D)

| 能力 | 实现 |
|------|------|
| `artifacts` 表 | `(slug, topic_id)` UNIQUE |
| `artifact_versions` 表 | `(artifact_id, version_label)` UNIQUE，version chain |
| `ArtifactSyncAdapter` ABC | 5 方法: create / update / read / list_versions / diff |
| `GitBackend` | 文件 + git commit，每个 artifact 一个文件 |
| Backend registry | `get_adapter("git", repo_path=...)` |
| 5 个 endpoint | `POST /api/artifacts`, `POST /:id/update`, `GET /:id`, `GET /:id/versions`, `GET /:id/diff` |

### Identity API

| Endpoint | Behavior |
|----------|----------|
| `GET /api/identity/me` | header-based: `X-Lets-Human` (required), `X-Lets-Human-Email` (opt), `X-Lets-Agent-Role` + `X-Lets-Device` (opt pair) |

### Test coverage

```
102 passed total:
  conftest harness                 (3 smoke)
  identity schema + helpers + API  (14)
  events schema + helpers + API    (8)
  topics schema                    (3)
  messages schema + helpers + API  (11)
  auth (tokens + CLI + dep + protection)  (15)
  MCP HTTP (mount + auth + tools/list + remote workflow)  (4)
  artifacts schema + adapter + git_backend + API  (29 in test_artifacts_*)
  legacy mirror (status/findings/feedback → messages)  (4)
  e2e PPT scenario (Track A)       (1)
  e2e artifact lifecycle (Track D) (1)
  rest: v1 baseline tests (work_items / agents / etc.)
```

---

## 3. Commit history (`track-d-artifacts`, 39 commits)

排序按 chronological（基线在底）。**B/D 在同一个 branch 上交错** —— Codex 把 Track B 误提交到了 `track-d-artifacts` 而非 `track-b-network`。代码无冲突。

```
adcbe15 test(mcp): integration test for remote token + tools/list + tools/call     [B-12]
ddcc19f docs: README section for v1.5 deploy + remote MCP                          [B-11]
a564c85 feat(deploy): docker-compose single-service config                          [B-10]
cd51766 feat(deploy): Dockerfile + env-controlled DB_PATH                           [B-9]
4726837 docs: README section for Track D (Artifact substrate)                       [D-13]
60b5f7d feat(mcp): switch .mcp.json to HTTP transport + add example template        [B-8]
ad0d8fa test(artifacts): end-to-end lifecycle (create + 2 updates + list + diff)    [D-12]
6871cb0 feat(artifacts): GET /api/artifacts/{id} endpoint with optional version    [D-11]
b6fae0a feat(artifacts): GET /api/artifacts/{id}/diff endpoint                      [D-10]
f32e0a9 feat(artifacts): GET /api/artifacts/{id}/versions endpoint                  [D-9]
0c070a0 feat(artifacts): POST /api/artifacts/{id}/update endpoint                   [D-8]
925cb23 feat(artifacts): POST /api/artifacts endpoint (Git, v0 initial)            [D-7]
1873d2c feat(mcp): mount authenticated streamable-http endpoint under /mcp         [B-6+7]
f84ee8d feat(artifacts): backend registry with git adapter                          [D-5]
a10905a feat(artifacts): GitBackend with 5 ABC methods                              [D-4]
a63d5de feat(auth): require Bearer token on /api/messages, /api/events             [B-5]
dc3cfd3 feat(artifacts): ArtifactSyncAdapter ABC + DB model helpers                 [D-3+6]
79b2a5e feat(auth): tokens CLI (issue/list/revoke)                                  [B-4]
085b8bc feat(auth): add FastAPI Bearer-token dependency get_current_principal       [B-3]
98c9cbb feat(auth): add token issue/verify/revoke helpers with sha256 hash storage  [B-2]
e8697ea feat(schema): add tokens table for bearer-token auth                        [B-1]
80c3b28 feat(schema): add artifact_versions table                                    [D-2]
e38f6ad feat(schema): add artifacts table                                            [D-1]
4f50cc7 test+docs: add e2e PPT scenario + README v1.5 schema notes                  [A-14+15]
50684e5 test(identity): cover GET /api/identity/me                                  [A-13 tests]
a32fdcc fix(events): remove duplicate events route definitions                      [A-7 fixup]
1c2fa12 feat(events): add record_event helper + POST/GET /api/events endpoints      [A-7 + A-13 endpoint mixed]
360afed feat(schema): add events append-only table with target/occurred_at indexes  [A-6]
7c13cd3 feat(identity): add ensure_human / ensure_agent_instance helpers            [A-5]
33bcaf2 feat(schema): add agent_instances with (role,human,device) uniqueness       [A-4]
e0c2b05 feat(schema): add agent_roles table with seeded claude/codex                [A-3]
969eeb6 feat(messages): mirror legacy status/findings/feedback to messages          [A-12]
71c448c feat(api): POST /api/messages + GET /api/topics/{id}/messages               [A-11]
349befd feat(schema): add humans table                                              [A-2]
1b135bd feat(messages): post_message + topic_stream helpers                          [A-10]
bfa3e9e feat(schema): add messages table with 13 typed variants                      [A-9]
36cc559 test(conftest): yielding client fixture + contract docstring                [A-1 fixup]
e426dc8 test: add pytest harness with temp DB and TestClient fixtures               [A-1]
b782477 chore: initial baseline (v1 + Lets rename + v1.5 plans/mock)                [baseline]
```

---

## 4. 怎么本地复现

```bash
# 0. Clone + setup
cd /Users/jacky/code/Lets
git checkout track-d-artifacts
.venv/bin/pip install -r requirements.txt

# 1. Initialize artifacts repo
mkdir -p ~/lets-artifacts && cd ~/lets-artifacts && git init && \
  git commit --allow-empty -m "init"
cd -

# 2. Run backend
export LETS_GIT_REPO=~/lets-artifacts
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000

# 3. Verify
curl http://127.0.0.1:8000/api/context
# {"project":{"name":"Lets",...}}

# 4. Issue a token + exercise auth-protected endpoints
.venv/bin/python -m app.tokens_cli issue --human admin --label local-dev
# ... (follow §5 demo below)

# 5. Full pytest
.venv/bin/pytest -v
# 102 passed
```

### Docker path

```bash
docker compose up -d
curl http://127.0.0.1:8000/api/context
docker compose down
```

---

## 5. Verified end-to-end (Track D demo, 2026-05-19)

| Step | Endpoint | Result |
|------|----------|--------|
| 1 | `python -m app.tokens_cli issue --human admin --label local-dev` | `lets_dfb0ffdb8a1c5d841979c8e55996c1d4` (token_id=3) |
| 2 | DB insert: `topics(slug='demo-ppt')` | `topic_id=1` |
| 3 | `POST /api/artifacts` with token + slug=q3-ppt | artifact_id=1, v0, git commit `652ec3b` |
| 4 | `POST /api/artifacts/1/update` v1 | git commit `dd23d93` |
| 5 | `POST /api/artifacts/1/update` v2 | git commit `e09406c` |
| 6 | `GET /api/artifacts/1/versions` | 3 versions chronological w/ summaries |
| 7 | `GET /api/artifacts/1/diff?from_label=v0&to_label=v2` | real unified `git diff` returned |
| 8 | `GET /api/artifacts/1` | content decoded to v2 terminal state |
| 9 | request without token → `401` | ✅ auth middleware works |
| 10 | physical inspection of `~/lets-artifacts/q3-ppt.pptx` | file exists; `git log` shows 3 commits matching API's SHA |

**Not yet verified** (but tests pass for them):
- Remote MCP connection from a 2nd machine
- Docker compose 'docker compose up' on a fresh host
- Multi-user (today's only "user" is `admin`)

---

## 6. 已知 gap / open issues

### 数据相关
1. **`humans.name UNIQUE` only** — no UNIQUE on email; multi-tenant rename in Track C will need a migration
2. **No `PRAGMA foreign_keys = ON`** in `app/db.py` — FK constraints are advisory; broken refs would silently slip through. Add to `connect()` in a hardening pass
3. **No ON DELETE CASCADE** on any FK — deletes are not in v1.5 surface so not biting, but Track C's "archive project" will need it

### Auth 相关
4. **No token rotation / TTL** — tokens live until manually revoked
5. **No rate limiting** on `/mcp/` or sensitive endpoints
6. **No web UI to manage tokens** — CLI only (Track E will expose this)
7. **`current_user` for legacy v1 endpoints unprotected** — `/api/work-items*`, `/api/status`, `/api/findings`, `/api/feedback` still don't require Bearer. Decision deferred to Track C (when project membership exists)

### Artifact 相关
8. **Only `git` backend** — `google-slides`, `feishu`, `object-storage`, `agentfs` are placeholder for v1.5c+
9. **`backend_ref` collision possible** — if two artifacts in different topics both slug to `hello.pptx`, both go to the same git file. Workaround: scope per topic dir (`{topic_id}/{slug}.{type}`); not yet implemented
10. **No preview rendering** — `preview_uri` column exists, no generator. PPT thumbnails come in v1.5c with Google Slides API
11. **Binary diff** — git diff of `.pptx` (binary zip) is useless; Google Slides backend in v1.5c will handle

### Branch 相关
12. **`track-d-artifacts` contains Track B work** — Codex committed Track B onto this branch instead of `track-b-network`. Three options: (a) accept and squash-merge as "v1.5b combined" (b) interactive rebase to split B and D (c) `git branch -m track-d-artifacts v1.5b-combined`. Recommendation: (a) or (c). See §7.

### Test 相关
13. **Several legacy v1 endpoints have no tests** — `/api/agents`, `/api/findings GET`, `/api/activity` etc. only smoke-covered by v1 baseline tests. Track C might revisit
14. **No CI** — pytest is run locally only

---

## 7. Branch hygiene recommendation

Three options for cleaning up:

### Option A: Squash merge as "v1.5b combined" 
```bash
git checkout master
git merge --squash track-d-artifacts
git commit -m "feat: v1.5 substrate complete (Track A+B+D, 102 tests)"
```
**Pros:** dead simple, one commit on master, clean.
**Cons:** loses per-task commit granularity for review.
**Recommended.**

### Option B: Rebase split B/D into two clean branches
Complex, ~30 minutes of surgical git work. Not worth it.

### Option C: Rename branch + non-fast-forward merge
```bash
git branch -m track-d-artifacts v1.5b-combined
git checkout master
git merge --no-ff v1.5b-combined
```
Keeps history; one merge commit on master. **Second choice.**

---

## 8. 下一步

| Item | Description | Estimated effort |
|------|-------------|------------------|
| **Merge Track F → main** | 24 commits ahead; PR open at github.com/jackylk/lets | 10 min |
| **Railway α 部署** | Dockerfile + docker-compose 已有；Railway 新建 service + Volume + GitHub OAuth env vars + 第一次登录 | 半天 |
| **第一个朋友 dogfood** | Issue GitHub OAuth client；同事 visit `/app` → 自助 token → 粘到本地 `.mcp.json` → CC 接入 | 0.5-1 天 |
| **Track G (Postgres)** | 真有第二个 active user 或 Railway autoscale 需要时再做 | 1 周（推后）|
| **Track E (Onboarding installer)** | macOS .dmg + daemon — v1.5b/c 范围，daemon 先不做 | 推后 |
| **v1.5c PPT 协作 demo** | Google Slides backend + Goal Guardian + nudge business logic | 等 v1.5a dogfood 反馈后 |

**Track F 自带的几个 follow-up（plan §Self-Review 已记录）**：
- `useSessionMe` 命名清理（现在是 `useSession` 的 re-export，可统一名字）
- Real artifact thumbnails — Track D adapter 已有 `preview_uri` 字段，前端 ArtifactPanel 还在画 generic SVG，需要等 Track D 的 GoogleSlidesBackend / preview URL 真生成
- @mention 解析对接真 directory — 当前 `SCRATCH_DIRECTORY` 硬编码在 TopicView，需要 `useDirectory()` query（依赖 backend `/api/directory` 端点，目前不存在）
- Design checkpoint A + B（typed-message 饱和度 + accent 色微调）— 第一轮 review pass 已做（去左 bar / bg /40→/25 / sidebar 真折叠 / composer 去外框），后续视觉细节按需迭代

---

## 9. 这次 dogfood 的几个发现（值得带进未来 plan）

1. **同一目录上多 worker 协作**真的能跑（CC + Codex 各自跑 subagent in 同一 cwd 同一 .git）—— 但需要 stash protocol + 不要 `git add -A`
2. **Codex 可能切错分支** —— Track B 的 7 commit 全跑到 `track-d-artifacts` 了。下次明示分支名 + 第一步必 `git branch --show-current`
3. **`stash --include-untracked` 在 untracked 文件多的时候会误抓自己刚 create 的文件** —— 改成 pathspec 显式 stash 或直接 `git add` 指定文件，更稳
4. **每 task TDD step 已经很精细，但**：Codex 自身有时会**合并多个 task 到一个 commit**（如 MCP mount + auth middleware）。问题不大，但合并 review 时要注意按 commit 而非按 task 排序
5. **CC vs Codex 分工**:
   - CC：Track D（抽象 ABC + adapter 设计）✅
   - Codex：Track B（系统集成 + Docker + MCP 协议）✅
   - 跟最初 `2026-05-19-tracks-overview.md` 的推荐完全一致
6. **plan 详细度合适** —— subagent 几乎不需要问额外问题，**plan 里 paste-ready code 块的策略起作用了**

---

## 10. STATUS.md 维护

每次完成一个 Track 或一组 task 时更新本文。它是"最近一次 sync"的 source of truth，比 commit log 更易读，比 roadmap.md 更具体。

下次大变更后请更新：
- §1 全景表
- §3 commit history（截断到最近）
- §6 open issues（划掉解决的、加新发现的）
- §8 下一步

记得 commit `docs/superpowers/plans/STATUS.md`。
