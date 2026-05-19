# Railway 部署前必须解决的 4 个 Gap

> **Snapshot at 2026-05-19** —— 本文档不是实现 plan，而是把 Lets 从"本地 dogfood"推到"Railway 公网 + 同事多人登录"之间的所有 backend gap 列清楚，作为后续 Track G / H / I 三个 plan 的入口。
>
> **前置假设**：本地阶段（Track C1 + Track C1.5 + Track F，约 2 周）已完成；本地 Web UI 跑通 PPT 场景；用户决定推到 Railway。

---

## 总览

| Gap | 痛点 | 后续 Track | 估时 |
|---|---|:---:|:---:|
| **G. SQLite → Postgres** | Railway 容器无状态；SQLite 文件挂在容器盘上，重部署清零 | Track G | **1 周** |
| **H. User login + OAuth** | 当前只有 CLI 发 Bearer token；Web 登录前提是多用户身份系统 | Track H | **1–2 周** |
| **I. Artifacts persistence** | `~/lets-artifacts/` 是本机 git repo；Railway 容器消失它就消失 | 嵌入 Track G | **0.5 天**（volume）or **1–2 天**（S3） |
| **J. Realtime push (WebSocket / SSE-over-HTTPS)** | Track C1.5 SSE 只在单进程进程内 queue 工作；Railway 多副本会丢消息 | Track I | **3–5 天** |

**总计**：约 **2.5–3 周**从"本地 dogfood-ready"到"Railway 公网可用、3 人同时在线协作"。

---

## Gap G — SQLite → Postgres

### 现状
- `app/db.py` 使用 stdlib `sqlite3`，`LETS_DB_PATH` env 指向本地文件
- 全部 102 个测试都跑在临时 sqlite 文件上
- Track C1 + C1.5 还要往 schema 上追加表 / 列

### 为什么必须换
- Railway 容器**没有持久磁盘默认**；要持久必须挂 **Volume**（区域绑定、单副本独占）
- 即使挂 Volume：多副本部署时 SQLite 不支持多写入；Railway autoscale 直接坏
- Postgres 是 Railway 原生 add-on，免运维

### 工作量拆解（1 周）

| 子任务 | 估时 |
|---|:---:|
| 抽象一层 DB driver（`app/db.py` 引入 `Engine` 概念，sqlite vs pg 走分支） | 1 天 |
| 重写所有 schema DDL 为 pg 方言（`AUTOINCREMENT` → `BIGSERIAL`/`IDENTITY`；`TEXT` 默认值；`PRAGMA` 替换为 pg 索引） | 1 天 |
| `connect()` `@contextmanager` 用 `psycopg[binary]` 或 SQLAlchemy Core | 0.5 天 |
| 把 `executescript` 改成迁移目录（`alembic` or 自写 `migrations/NNN_*.sql`） | 1 天 |
| CI 跑双轨：sqlite 仍跑（保留 fast local test），新增 pg service container 跑同一套测试 | 1 天 |
| 修 21 处 SQL 兼容性问题（CHECK 约束写法、`?` vs `%s` placeholder、`PRAGMA table_info` → `information_schema`） | 1 天 |
| Railway 接 Postgres add-on + `DATABASE_URL` env wiring + 验证 cold start | 0.5 天 |

### 决策点
1. **要不要用 ORM？** 推荐**不用**（SQLAlchemy ORM）；继续手写 SQL，仅借 SQLAlchemy Core 的连接池和 driver 抽象。理由：当前代码风格直白，引入 ORM 会扰动 102 个测试。
2. **如何保留 sqlite 本地路径？** 测试时仍走 sqlite（fast），生产走 pg。`db.py` 看 `DATABASE_URL` 是否存在决定 driver。
3. **migration tool？** 推荐**自写**目录 + sequence number。Alembic 对项目当前规模过重。

### 不在本 Track 范围
- 多 region/replication（Railway 单 region 起步）
- 读写分离（v1.5 用不到）

---

## Gap H — User login + OAuth

### 现状
- Bearer token 只能 CLI `python -m app.tokens_cli issue --human admin` 发
- `humans.name` 是 UNIQUE 字符串，没有密码或第三方账号绑定
- 前端 `IdentityProvider` 用 `X-Lets-Human` header（明文 trust）

### 为什么必须改
- Railway 公网；任何人能伪造 `X-Lets-Human: Neo` header
- 同事要登录界面，不可能让他们 ssh 到容器跑 tokens_cli
- 多人协作的最基础前提：知道"现在敲键盘的是谁"

### 推荐方案：GitHub OAuth（first option）
**理由**：
- 目标用户是开发者；99% 有 GitHub 账号
- 不用做密码管理 / 找回 / 验证邮箱
- 顺便能拿到 GitHub username 作为 `humans.name`，未来 Track C2 接 GitHub repo 时复用 token

**备选**：Google OAuth（开发者也都有），Email magic link（需 SMTP）

### 工作量拆解（1–2 周）

| 子任务 | 估时 |
|---|:---:|
| `humans` 表加列：`oauth_provider`, `oauth_subject`, `avatar_url` | 0.5 天 |
| 新表 `sessions` (session_id, human_id, expires_at, ip, user_agent) | 0.5 天 |
| FastAPI OAuth callback (`/auth/github/start`, `/auth/github/callback`) + cookie session | 1 天 |
| 前端 `/login` 页面 + `IdentityProvider` 改用 cookie session（去掉 `X-Lets-Human` header trust） | 1 天 |
| Bearer token 改为"通过 web 登录后，进设置页生成给 CLI 用"（不再 CLI 直发） | 1 天 |
| 改造现有 102+ 测试：注入 session cookie 而非 `X-Lets-Human` | 1 天 |
| 测试：未登录访问 `/api/*` → 重定向到 `/login`；MCP `/mcp/` 仍走 Bearer token（CLI agent 友好） | 0.5 天 |
| Railway env：`GITHUB_OAUTH_CLIENT_ID/SECRET`，回调 URL whitelist | 0.5 天 |
| 多 project 授权模型：每 project 维护 `project_members(project_id, human_id, role)` | 1–2 天 |

### 决策点
1. **是否要 admin 邀请制？** 推荐 v1 是；新登录用户默认进 "pending"，需 admin（你自己）approve 才能加入 project。否则任何人来都能进。
2. **MCP 怎么办？** MCP `/mcp/` 保留 Bearer token 流；web 用户在设置页面"为本地 CLI 生成 token"。本地 CLI 用 token，浏览器用 session cookie。两套并存。
3. **Cookie 安全：** `SameSite=Lax`, `Secure`, `HttpOnly`. 30 天到期，使用刷新。
4. **CSRF**：所有 mutation endpoint 需 CSRF token 校验（或仅 fetch + custom header `X-Lets-Token`）。

### 不在本 Track 范围
- 团队/组织树（v1 只有 project 级 membership）
- SSO / SAML
- 2FA

---

## Gap I — Artifacts persistence

### 现状
- Track D `GitBackend` 写入 `LETS_GIT_REPO` 指向的本地 git repo
- 本机 `~/lets-artifacts/` 是个 git repo，artifact API 通过 subprocess `git` 写
- Railway 容器是临时的 → repo 被冲掉

### 选项对比

| 方案 | 优 | 劣 | 估时 |
|---|---|---|:---:|
| **A. Railway Volume + git repo** | 改动最小（沿用 GitBackend） | Volume 区域绑定、单副本；备份要自己搞 | **0.5 天** |
| **B. S3-compatible object storage** | 持久、多副本友好、备份天然 | 失去 git diff/history 语义；需写 `S3Backend` adapter | **1–2 天** |
| **C. 远程 GitHub repo** | history 完整、UI 现成、零运维 | 每次 commit/push 慢 1–3s；rate limit | **1 天** + Track C2 OAuth 前提 |

### 推荐路线
- **Railway 起步用 A（Volume）**：把 `LETS_GIT_REPO=/data/lets-artifacts` 挂到 Volume；GitBackend 不改
- **同时存 B 作为冷备**：单独 cron 任务每天 `git archive | aws s3 cp` 备份到 S3
- **C 留给 v1.5c**：用户 link 自己的 GitHub repo 当 artifact backend（每个 project 可选）

### 实施细节（路线 A，0.5 天）
1. Railway Dashboard → service → Volumes → mount `/data`
2. `Dockerfile`：`ENV LETS_GIT_REPO=/data/lets-artifacts`
3. 启动脚本：`if [ ! -d "$LETS_GIT_REPO" ]; then git init "$LETS_GIT_REPO" && cd "$LETS_GIT_REPO" && git commit --allow-empty -m init; fi`
4. `docker-compose.yml` 添加 named volume for local dev parity

### 决策点
- **是否在 v1.5b 就上 S3 adapter？** 不推荐。Volume 够用先发；上线后再看是否需要换。adapter 已经是 ABC，将来切换不破坏。

---

## Gap J — Realtime push (Postgres LISTEN/NOTIFY 或 Redis Pub/Sub)

### 现状（Track C1.5 之后）
- `app/sse.py` 用进程内 `asyncio.Queue` per topic
- 单进程 fine；Railway 单副本起步也 fine

### 为什么以后必须改
- 用户增长 → Railway autoscale → 副本 A 收到 `POST /api/messages` → 副本 A 内 queue 推送 → 订阅副本 B 的浏览器**收不到**
- 这是 silent failure，最难 debug

### 选项

| 方案 | 优 | 劣 | 估时 |
|---|---|---|:---:|
| **A. Postgres LISTEN/NOTIFY** | 不引入新组件（已经有 pg） | payload < 8KB 限制；pg connection 占用 | **2 天** |
| **B. Redis Pub/Sub** | 标准方案、高吞吐 | 多一个 Railway add-on（$） | **3 天** |
| **C. WebSocket + sticky session** | 不需要 pub/sub 后端 | Railway autoscale 下需要 sticky；运维复杂 | 不推荐 |

### 推荐路线 A（Postgres LISTEN/NOTIFY，2–3 天）
**Track G（pg 迁移）做完之后顺势做**，不需要新组件。

实现：
1. `POST /api/messages` 写库成功后 `NOTIFY topic_<id>, '<json>'`
2. SSE handler 连一个独立 pg connection 跑 `LISTEN topic_<id>`，收到通知就 forward 给浏览器 client
3. 每副本独立 LISTEN，所有副本收到所有副本的 NOTIFY
4. payload 超 8KB（unlikely for chat）就只 NOTIFY message_id，handler 自己 SELECT 取全文

### 决策点
- **WebSocket 还是 SSE？** SSE 已经能跑；除非要加 typing indicator / cursor sharing 这种双向场景再上 WS。
- **Redis 何时引入？** > 10 副本 / > 100 并发用户。早期不需要。

### 不在本 Track 范围
- 离线消息回放（用户离线时累积，重连一次性下发）—— 实际上用 `/api/topics/{id}/messages?after_id=...` 已经能做
- Push notification（webpush / APN）—— Track L 或更晚

---

## 三个后续 Plan 的占位

```
docs/superpowers/plans/2026-XX-XX-track-g-postgres-migration.md      [待写]
docs/superpowers/plans/2026-XX-XX-track-h-oauth-login.md             [待写]
docs/superpowers/plans/2026-XX-XX-track-i-realtime-multi-replica.md  [待写]
```

每个 plan 应包含：
- 现状代码引用（具体 file:line）
- TDD 任务拆解（fail-first → green → commit）
- migration 兼容性验证（老数据不丢、老 token 不废）
- Railway 部署校验步骤（deploy preview + smoke）

---

## 推荐总顺序

```
现在 (Track C1 plan-ready, 102/102 tests green)
  ▼
Track C1 (本地 projects, 2-3 天)
  ▼
Track C1.5 (Web UI backend glue, 3-4 天)    ←─ 见 TRACK-C1-WEBUI-RECONCILIATION.md
  ▼
Track F (Web 前端, 1 周)
  ▼
本地 dogfood 1 周（你 + Codex + Claude Code 三方在本地跑 PPT 协作）
  ▼
🚀 决定推 Railway
  ▼
Track G (Postgres + Volume artifacts, 1 周)
  ▼
Track H (OAuth + multi-user, 1-2 周)
  ▼
Track I (LISTEN/NOTIFY multi-replica realtime, 0.5 周)
  ▼
公测：邀请 2-3 个同事
  ▼
v1.5c：PPT collaboration demo with Google Slides API
```

**关键里程碑日期估算**（基于 2026-05-19 起步）：
- 本地 dogfood：**2026-06-09** 左右
- Railway 公网内测：**2026-07-07** 左右
- v1.5c PPT demo：**2026-08 月**

---

## 不属于"必须"的部署 gap

下列项目不阻塞 Railway 公网上线，可以后续按需补：
- 监控 / 日志聚合（先用 Railway 自带 log viewer）
- 备份策略（pg 自动 daily snapshot 已经够 v1.5）
- CDN（静态资源不大）
- 多 region（用户都在国内一开始）
- email transactional（OAuth 不需要；通知改用 in-app）
- 限流 / WAF（量小先看 Railway 默认；后期上 Cloudflare）

---

## 一句话总结

**Railway 公网上线 = pg + login + 持久 artifact + 跨副本 realtime**。前三个是阻塞型，第四个是 silent failure 型；任何一个跳过，要么"推上去用不了"，要么"用着用着发现消息丢了"。
