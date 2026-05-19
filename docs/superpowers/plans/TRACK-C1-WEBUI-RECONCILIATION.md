# Track C1 ↔ Track F Reconciliation

> **Snapshot at 2026-05-19**.  对照 `2026-05-19-track-c1-local-projects.md` (10 tasks, projects + topics + spec view) 与 `2026-05-19-track-f-web-frontend.md` (11 phases, Vite + React 前端) 后，列出**前端需要、但 C1 没有覆盖**的后端接口与字段。
>
> 结论：C1 + Track A/B/D 已经能让前端跑通 **Phase 0–4**（脚手架 / 契约层 / 应用骨架 / 4 种简单消息 / 9 种复杂 typed message 渲染）和 **Phase 5 大部分**（POST/GET messages）。**真正缺的是 Phase 5 的 SSE、Phase 6 的 context pane 数据源、Phase 7 的 attention queue、Phase 8 的 spec write-back、Phase 9 的 goal 字段**。

---

## 1. C1 与 Track F 的接口对齐情况

| Track F 列出的 backend addition | C1 提供？ | 状态 |
|---|---|---|
| `GET /api/topics` (全局列表) | ❌ C1 改为 `GET /api/projects/{id}/topics` | **Track F 需要更新**：去掉全局列表，改用 project-scoped |
| `POST /api/topics` (全局创建) | ❌ C1 改为 `POST /api/projects/{id}/topics` | **Track F 需要更新**：路由变为 project-scoped |
| `GET /api/topics/{id}/stream` (SSE) | ❌ | **C1.5 新任务** |
| `/app` 静态挂载 + SPA fallback | ❌ | **C1.5 新任务**（FastAPI `StaticFiles`） |

Track A/B/D 已有的前端需要：
- `GET /api/identity/me` ✅
- `POST /api/messages` ✅
- `GET /api/topics/{id}/messages?type=...` ✅
- `POST/GET /api/events` ✅
- `/api/artifacts*` 全套 ✅
- `/mcp/` 带 Bearer ✅

C1 新增前端会用到的：
- `POST /api/projects` ✅
- `GET /api/projects` ✅
- `GET /api/projects/{id}` ✅
- `PATCH /api/projects/{id}` ✅
- `POST /api/projects/{id}/topics` ✅
- `GET /api/projects/{id}/topics` ✅
- `GET /api/topics/{id}` ✅
- `GET /api/projects/{id}/spec?include_content=true` ✅
- `project_proposal` typed message 约定 ✅（doc-only）

---

## 2. Track F 需要、C1 没有的后端工作（待补）

### Gap 1 — Live update：`GET /api/topics/{id}/stream` (SSE)

**Track F Phase 5 demo 要求**："两个浏览器 tab 看到彼此的发言。"

**实现量级**：~半天。FastAPI `StreamingResponse` + 一个进程内 `asyncio.Queue` per topic。新消息 POST 后向所有订阅者推送 JSON line。无需 Redis，单进程够 v1.5b 用。

**建议任务拆解**：
1. `app/sse.py` — `TopicBroadcaster` 类（per-topic queue 列表，subscribe/publish）
2. `POST /api/messages` 在写库成功后调用 `broadcaster.publish(topic_id, msg_dict)`
3. `GET /api/topics/{id}/stream` 返回 `text/event-stream`，每行 `data: {json}\n\n`
4. 用 `httpx.AsyncClient` 的 `stream()` 写 1 个 pytest 集成测试
5. 心跳：每 15s 推 `:ping\n\n` 防 proxy 超时

**Track F 已留 fallback**：前端 `api/sse.ts` 失败时退化为 5s 轮询 `/api/topics/{id}/messages?after_id=…`。但 `after_id` 增量过滤参数也得加（小改动）。

---

### Gap 2 — Attention queue (Phase 7 整个用得到)

**Track F 要求**：sidebar 顶部"待处理(N)"+ AttentionView 三个分组（"需要决策" / "@你的提问" / "建议"）。

**数据需求**：跨 topic 聚合，按 actor `addressed_to` / typed message type 过滤。

**目前缺**：
- `messages.addressed_to` 字段 ✅ 已存在（Track A 加的）
- 但**没有跨 topic 的聚合 endpoint**

**建议**：新增 `GET /api/attention` — 参数 `?human_id=N`，返回三组：
```json
{
  "needs_decision": [<message rows + topic context>],
  "mentioned_questions": [...],
  "suggestions": [...]
}
```
分组规则（v1.5b 简化版）：
- needs_decision：`type=question OR type=spec_change OR type=task_tree_proposal`，且 `addressed_to` 含本人，且无后续 `decision` 引用
- mentioned_questions：`addressed_to` 含本人，但不在上面分组里
- suggestions：`type=proactive_finding` 且 `addressed_to` 含本人

**实现量级**：1 天。SQL 三条 query + 一个聚合 endpoint。

---

### Gap 3 — Context pane 数据源（Phase 6 五块面板）

| Track F 面板 | 数据从哪来 | 缺什么 |
|---|---|---|
| TopicInfoCard | `GET /api/topics/{id}` | ✅ C1 已有 |
| TaskTreePanel | 派生自 `type=task_tree_proposal` 的最新消息 | 需要约定 `metadata.task_tree` shape；endpoint 可复用 `/messages?type=task_tree_proposal&limit=1`，前端自己拿最新一条 |
| ArtifactPanel | `GET /api/artifacts?topic_id=N` + `/versions` | **缺 `?topic_id` 过滤**：当前 `GET /api/artifacts/{id}` 只能按 id 查，没有"列出本 topic 下所有 artifact"的 endpoint |
| SpecTouchedPanel | 派生自 `type=spec_change` 的消息（按 `metadata.file` 去重） | ✅ 现有 `/messages?type=spec_change` 就够，前端聚合 |
| ParticipantsPanel | 派生自本 topic 所有 actor_id + identity 表 | **缺**：`GET /api/topics/{id}/participants` 返回去重后的人 + agent 列表 |
| GitRow | 最新 commit / dirty 状态 | **缺**：`GET /api/projects/{id}/git-status` —— 只读，跑 `git -C {repo_path} status --short` + `log -1` |

**新增任务**：
- `GET /api/artifacts?topic_id=N`
- `GET /api/topics/{id}/participants`
- `GET /api/projects/{id}/git-status`

**实现量级**：合计 1 天。

---

### Gap 4 — Goal Card 字段（Phase 9）

**Track F 要求**：topic 顶部的 GoalCard 显示"目标 Artifact + 进度 + Mark as Final"。

**目前缺**：
- topic 没有 `goal_text` / `goal_artifact_id` / `goal_progress` 字段
- artifact 没有 `is_final` 状态

**建议（v1.5b 极简版，避免新表）**：
- 不加 topic 列；goal 改成"topic 内最新一条 `type=goal_proposal` typed message"承载（mock 已经按此设计）
- `goal_proposal` 需要加入 `messages.type` CHECK 约束（**Track A 没预留**，需要 ALTER）
- "Mark as Final" 在前端发一条 `type=decision` + `metadata.decision_type="mark_final" + artifact_id=N` 的消息；后端不需要新 endpoint

**Track A CHECK 约束改造**：SQLite 不支持 `ALTER … ADD CONSTRAINT`，需要 table rebuild。可以作为 C1 Task 11（migration 任务）：
1. 建 `messages_new` 含新 CHECK
2. `INSERT INTO messages_new SELECT * FROM messages`
3. `DROP TABLE messages; ALTER TABLE messages_new RENAME TO messages`
4. 重建索引

**实现量级**：半天（含 migration + 测试）。

---

### Gap 5 — Spec change write-back（Phase 8）

**Track F 要求**："Spec change diff modal, 通过/拒绝按钮 wired to backend ⇒ spec change roundtrip works"。

**目前缺**：approve 一个 spec_change 后，需要把 `metadata.after` 写回 `repo_path/<file>`。C1 的 `GET /api/projects/{id}/spec` 是只读的。

**建议**：`POST /api/projects/{id}/spec/apply` — body `{file: "...", content: "..."}`，原子写文件（写临时文件 + `os.replace`），追加一条 `type=system` 消息记录"applied by <human>"。**不做 git commit**（v1.5b 范围内）。

**安全**：仍用 `Path(repo_path).resolve()` + `relative_to` 校验（C1 Task 7 已有的模式）。

**实现量级**：半天。

---

### Gap 6 — SPA 静态挂载

**Track F Phase 11 要求**：`pnpm build` → FastAPI 在 `/app` 提供 SPA。

**建议**：在 `app/main.py` 末尾：
```python
from fastapi.staticfiles import StaticFiles
from pathlib import Path

_FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"
if _FRONTEND_DIST.is_dir():
    app.mount("/app", StaticFiles(directory=_FRONTEND_DIST, html=True), name="spa")
```

**实现量级**：10 分钟。SPA fallback 由 `StaticFiles(html=True)` 处理。

---

### Gap 7 — Agent presence "Online" section

**Track F 要求**：sidebar `OnlineSection` 显示当前在线的 agent。

**目前缺**：`agent_instances` 没有 `last_seen_at` 列；MCP 调用时不更新心跳。

**建议（v1.5b 最简）**：
- 不加新列，直接用 `tokens.last_used_at` 推算："过去 5 分钟内 token 用过的 agent_instance_id"
- `GET /api/agents/online?project_id=N` 返回过去 5 分钟活跃 agent 列表
- 不强求心跳；如果 5 分钟没动作就算离线

**实现量级**：半天。需要确认 token issuance 时是否绑 `agent_instance_id`（Track B `issue_token` 接受这个参数，需校验有写入）。

---

### Gap 8 — Direct messages

**Track F sidebar** 有 DM section。**v1.5b 不实现**：DM 模型涉及私聊权限语义、加密考虑，延后到 Track C2 或更晚。前端 DM section 可先显示空 placeholder。

---

## 3. 推荐拆分：Track C1.5 "Web-UI Backend Glue"

把上面 Gap 1–7 合成一个独立 plan（约 7 个新 task，估 3–4 天），命名 **Track C1.5**，跑在 C1 之后：

| Task | 内容 | 估时 |
|---|---|---|
| 1 | SSE: `GET /api/topics/{id}/stream` + `?after_id=` 增量过滤 | 半天 |
| 2 | Attention: `GET /api/attention` 跨 topic 聚合 | 1 天 |
| 3 | Context pane: `GET /api/artifacts?topic_id=`, `/topics/{id}/participants`, `/projects/{id}/git-status` | 1 天 |
| 4 | Goal: `goal_proposal` 加入 CHECK + messages 表 rebuild | 半天 |
| 5 | Spec write-back: `POST /api/projects/{id}/spec/apply` | 半天 |
| 6 | SPA mount: `/app` StaticFiles | 10 分钟 |
| 7 | Online: `GET /api/agents/online` 基于 token.last_used_at | 半天 |

**前置**：Track C1 完成（10 task）。

**触发后续**：Track F 全部 Phase 解锁。

---

## 4. Track F 计划文件本身的修订建议

把这几条直接挂回 Track F plan（要么手改 `2026-05-19-track-f-web-frontend.md`，要么在 Track F 执行时补丁）：

1. **去掉 "Backend additions: GET /api/topics, POST /api/topics"** —— 改用 C1 的 project-scoped endpoint。前端的 `Sidebar/ChannelsSection` 需要先拿 project_id，再拉该 project 的 topic 列表。
2. **Phase 5 增加："切换前先确认 Track C1.5 Task 1 完成"** —— SSE 没就退化轮询，但要明说。
3. **Phase 6 ArtifactPanel** —— 改成 `GET /api/artifacts?topic_id=N` 而不是 `/api/artifacts/{id}`。
4. **Phase 7 AttentionView** —— `useAttention()` hook 调 `/api/attention`，不是前端自己 grep 所有 topic。
5. **Phase 9 GoalCard** —— `goal_proposal` typed message 是数据源；不要单独的 `/api/topics/{id}/goal` endpoint。
6. **Phase 11 SPA mount** —— 改成"修改 app/main.py 末尾追加 StaticFiles 5 行"，不需要新文件。

---

## 5. 多 project 导航：UX 调整

C1 引入 projects 后，前端 sidebar 顶部需要一个 **Project Switcher**（Mock 现在只显示单个项目名）。建议形态：

- 左上角项目名变成 Dropdown：`▾ Q3 Review`
- 点击展开 `GET /api/projects` 返回的列表，可切换；底部 "+ New Project" 触发 `POST /api/projects`
- URL 加 query param `?project=<slug>`，刷新保留选择
- Topic 列表、Attention queue、Spec view 都 scope 到当前 project

**这是 Track F 当前 mock 没考虑的形态变化**，属于"UX 改造"，不是 backend gap。建议在 Track F 执行前补一稿 mock 验证。

---

## 6. 推荐执行顺序

```
现在 ──► Track C1 (10 tasks, 2-3 天)
       │
       ├─► Track C1.5 (7 tasks, 3-4 天)  [本文档列的 backend gap]
       │
       ├─► 更新 Track F mock + plan（UX 调整 + endpoint 路径改写, 半天）
       │
       ├─► Track F Phase 0–5 (脚手架 + 契约 + 4 种简单消息, 2 天)
       │
       ├─► Track F Phase 6–9 (context pane + attention + spec + goal, 3 天)
       │
       ├─► Track F Phase 10–11 (mobile + e2e + SPA mount, 1 天)
       │
       └─► 本地 dogfood 1 周
       
       然后才进入 Railway 部署（见 RAILWAY.md：Track G/H/I）
```

总计本地阶段：约 **2 周**到 dogfood-ready。
