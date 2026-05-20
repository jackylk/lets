# 交接给 Codex — 把 Lets 推到 Railway 真实可用

> **Owner**：Codex
> **Goal**：让 Jacky 能在 https://lets.up.railway.app/ 上做完整的 onboarding
> 流程 —— GitHub OAuth 登录、一键启动本地 gateway、邀请同事进同一 project、
> 重启电脑后 gateway 自动连回来。完成之后 Jacky 用 Slack 一样自然地用 Lets。
>
> **Branch**：直接在 `main` 上推。两个 CC 实例都在 main 上协作（commit 后
> `git update-ref refs/heads/main HEAD` 保持同步）。
>
> **Status snapshot when this doc was written**：HEAD = `3f7df7f` (+ 一个
> 待 commit 的 rename `agent_runner.py → gateway.py`)。Railway 上的 `lets`
> service 正在跑 commit `39c79fd` 附近的版本（auto-deploy）。本地全栈
> 已经验证跑通真实流程（人在浏览器发 `@cc <task>` → 本地 Claude Code
> 真生成回复 → 出现在 web）。

---

## 1. 当前可工作的真实流程（已验证）

完整链路：

```
浏览器（127.0.0.1:8000/app/）
    ↑↓  session cookie auth
FastAPI backend (app/main.py, app/auth.py, app/db.py)
    ↑↓  /api/* + /mcp/ HTTP
本地 gateway 进程（app/gateway.py，每个 agent_instance 一个）
    ↓ subprocess: claude --print "<prompt>"
本地 Claude Code CLI
```

`/api/messages` POST 时，如果 `addressed_to` 含某 human 的 id，本地
gateway 会 ~3s 内拿到这条消息，构造带 topic context 的 prompt，spawn
`claude --print "<prompt>"`，把 CC 的 stdout 当 reply 发回 topic。

**已经实测的 dogfood DB**：`/tmp/lets-smoke.db`，project_id=4
("Rome Trip PPT")，topic_id=1。topic 流里 message #11 是真实 Claude Code
生成的总结，不是脚本。

**已经有的脚手架**：

- `scripts/connect_local_agents.sh Jacky` —— 给指定 human 发两个 agent-bound
  token，写到 `~/.mcp.lets/<human>/{cc,codex}.mcp.json`
- `scripts/lets-supervisor.sh Jacky` —— 启两个 gateway（CC + Codex），日志
  到 `/tmp/lets-gateway-{cc,codex}.log`
- `app/sessions_cli.py` —— dev-only：给 human 直接发 session cookie 值，
  绕开 OAuth（**生产环境不暴露**）

**已经在的依赖**（Jacky 本机上）：

- `~/.local/bin/claude` 2.1.144 (Claude Code CLI)
- `/usr/local/bin/codex` 0.130.0 (Codex CLI)
- `.venv/bin/python` Python 3.13 with `httpx`, `mcp` etc.

---

## 2. Railway 部署现状 + gap

### Railway 服务

- Project: `027785b0-e605-4d3c-b04e-54b08b3c2b37`
  ([dashboard](https://railway.com/project/027785b0-e605-4d3c-b04e-54b08b3c2b37/service/770b8b4e-d68a-4a6b-b3b8-ddfbff310bb1?environmentId=e58577f3-8e46-439c-bd94-03157d5e7a2f))
- Service: `770b8b4e-d68a-4a6b-b3b8-ddfbff310bb1`
- Domain: `https://lets.up.railway.app`
- 上次 deploy 历史看 `gh api repos/jackylk/lets/deployments?per_page=5`
- **本机 Railway CLI 当前坏掉**（`Failed to fetch: error decoding response body`），
  CLI 调用 `railway logs` / `railway run` 都 502 backboard。需要在 Railway
  网页 dashboard 看 logs。

### 已有的 env vars（按 Dockerfile）

```
LETS_DB_PATH=/data/lets.db
LETS_GIT_REPO=/data/lets-artifacts
LETS_FRONTEND_DIST=/app/frontend/dist
GITHUB_CLIENT_ID=<你已在 Railway 设了？请确认>
GITHUB_CLIENT_SECRET=<同上>
GITHUB_REDIRECT_URI=https://lets.up.railway.app/auth/github/callback
LETS_COOKIE_SECURE=true   # production 默认即 true
```

### Volume

- `/data` 是 Railway Volume，sqlite + artifact git repo 持久化在这里
- `scripts/docker-entrypoint.sh` 已经在 `/data/lets-artifacts` 没初始化时
  `git init` 一次

### 当前 gap（这是 Codex 的工作）

| # | gap | 现状 | 影响 |
|---|---|---|---|
| 1 | Railway 部署最近经常 fallback 404 | edge `x-railway-fallback: true` 持续返回 | 试用前必须先确认 deploy healthy |
| 2 | gateway 没法装在 Jacky 同事的电脑上 | 必须 clone 整个 repo + 跑 `python -m app.gateway` | onboarding 流被卡死 |
| 3 | 邀请同事流不存在 | 单用户 OAuth；同事即使登录了也看不到 Jacky 的 project | 不能真的协作 |
| 4 | 重启电脑后 gateway 死 | nohup 进程，关机就没了 | 老用户体验差 |
| 5 | 首次进站没有 wizard / tutorial | 进去看空 sidebar，不知道下一步 | 留存差 |

---

## 3. 这次交接给 Codex 的具体任务

按优先级。每一项都包含验收标准 — 跑过验收标准才算完成。

### 任务 A：先把 Railway 现状摸清并修活（**必做，先做**）

**步骤：**

1. 用 web 浏览器登录 Railway dashboard，看 `lets` service 最近的 deploy。
   - 如果 deploy 失败 → 看 build logs，把 root cause 列出来
   - 如果 deploy 成功但容器 crash → 看 runtime logs，找 stacktrace
2. 在 dashboard 复制最后 100 行 runtime logs 贴到 `/tmp/railway-logs-2026-05-20.txt`
3. 如果是数据库 migration 失败（很可能是 commit `066c25b` 引入的
   `_migrate_topics_mode` rebuild 在 PRAGMA foreign_keys=ON 时炸），我已经
   在 `a162b97` 加了 FK-safe wrap，但可能还不够 —— Railway 重启 service
   看是否复活
4. 验证 `curl https://lets.up.railway.app/api/context` 返回 200 JSON，
   不是 `x-railway-fallback: true`

**验收**：上面 curl 在 Railway dashboard 显示 deploy active 之后必须返回 200。

### 任务 B：把 `lets-gateway` 拆成独立 pip 包 / 安装脚本（**对 onboarding 至关重要**）

让新用户不需要 clone 整个 Lets repo 就能跑 gateway。

**两个可选方案，挑一个：**

**方案 B1（推荐，最快）**：写一个一行 install + run 脚本

```bash
curl -fsSL https://lets.up.railway.app/install/gateway.sh | bash
```

backend 加一个 `GET /install/gateway.sh` 端点返回 shell 脚本，脚本干这些：

1. 检测 Python 3.10+
2. `python -m venv ~/.lets/venv`
3. `~/.lets/venv/bin/pip install httpx`
4. 把 `app/gateway.py` 单文件下载到 `~/.lets/gateway.py`
5. 提示用户：先 `lets login`（见任务 C），然后 `bash ~/.lets/run-gateway.sh`

**方案 B2**（更正经，但慢）：发一个 `lets-gateway` 到 PyPI

- 把 `app/gateway.py` 抽到自己的小 package: `lets_gateway/`
- `pyproject.toml` console_scripts: `lets-gateway = lets_gateway.main:cli`
- 用户 `pip install lets-gateway` 然后 `lets-gateway --token ...`

**推荐先做 B1**，B2 留给后续。

**验收**：在另一台电脑（或新建 macOS user account）上跑那个 one-liner，
能从零开始把 gateway 跑起来，浏览器 `/app/` 上看到这个 agent 上线。

### 任务 C：`lets login` — 一键 OAuth 拿 token

新增 backend endpoint：

- `GET /auth/device-flow/start` —— 给本地 gateway 一个 `device_code` + 一个
  `verification_url`。展示 url 给用户，让他手机/浏览器打开
- 用户在浏览器登录 OAuth + 看到一个 device 码确认页面（参考 GitHub device
  flow）→ 点 "授权这个 device" → backend 把 device_code 标记为 authorized
  并绑到 (human_id, agent_instance_id)
- gateway 端 `GET /auth/device-flow/poll?device_code=...` 直到 authorized，
  拿到 token + 保存到 `~/.lets/token.json`

把这个流封装成 `lets-gateway login` 子命令（args 改成 `lets-gateway login` /
`lets-gateway run`）。

**验收**：用户在 terminal 跑 `~/.lets/venv/bin/python ~/.lets/gateway.py login`
打印一个 url → 用户浏览器打开（已经 OAuth 登录过）→ 点确认 → terminal
自动拿到 token 并写本地。下一句 `~/.lets/venv/bin/python ~/.lets/gateway.py run`
即可上线。

### 任务 D：邀请同事流

后端：

- 新表 `project_members(project_id, human_id, role enum('owner','member'), joined_at)`
  - 现有的 4 个 project 在 migration 里都加 owner = `owner_human_id`
- 新表 `invites(id, project_id, code TEXT UNIQUE, created_by_human_id, expires_at, redeemed_by_human_id, redeemed_at)`
- `POST /api/projects/{id}/invites` (auth: project owner) → 返回 `{code, url: https://.../invite/<code>}`
- `GET /invite/{code}` (public route) → SPA 路由，前端显示 "<owner> 邀请你加入
  <project_name>" + "用 GitHub 登录加入" 按钮
- 登录 callback 时如果 query string 有 `invite=<code>` 则也加 member 行

前端：

- Settings 页加 "邀请同事" tab，列已发出的 invites + "新建邀请" 按钮
- `/invite/<code>` 路由：未登录 → GitHub OAuth；登录后 → 自动加入 + 重定向到
  project 的第一个 topic

权限：

- 现有 `/api/projects/{id}/topics`、`/api/topics/{id}/messages` 等接口必须加
  membership 校验。owner + member 都能读写，非 member 401

**验收**：Jacky 自己创建邀请 → 复制 url → 用浏览器无痕模式登录另一个 GitHub
账号（同事模拟）→ 自动加入项目 → 看到 Jacky 的 topic + 在 topic 里 @ 一下 Jacky。

### 任务 E：gateway 开机自启（macOS launchd）

`lets-gateway install` 子命令：

- 写 `~/Library/LaunchAgents/com.lets.gateway-<role>-<device>.plist`
- 内容指向 `~/.lets/venv/bin/python ~/.lets/gateway.py run --token <saved>`
- `RunAtLoad=true`, `KeepAlive=true`
- `launchctl load ~/Library/LaunchAgents/com.lets.gateway-...plist`

`lets-gateway uninstall` 反向。

**验收**：用户跑 `lets-gateway install` → 重启电脑 → 不用做任何事，浏览器
打开 lets，sidebar Agent 行有绿点。

### 任务 F（可推到 F+1）：首次登录 wizard + Tutorial topic

OAuth 注册新 human 时，自动：

1. 给他建一个 "Welcome" project + "Hello" topic
2. 在 topic 里 seed 一条 system 消息 "在 composer 里 @cc 介绍一下你自己，
   试试看本地 CC 能不能回话。如果没装 gateway，先去 Settings → Agent Tokens"

前端 `/app/` 首次进入（topics.length === 1 && 第一条消息是 system "Welcome"）
显示一个 onboarding bar 引导。

---

## 4. 代码地图（让 Codex 快速进入）

- **Backend**：`app/main.py` 是 FastAPI 总线，~1800 行。所有 route 都在这里
- **Auth**：`app/auth.py` —— token issue/verify + session cookie + ContextVar 
  for MCP principal
- **DB**：`app/db.py` —— sqlite schema + idempotent migrations。CHECK rebuild
  pattern 用过两次（project_proposal + goal_proposal），是新 typed message 
  必须 rebuild 的模板
- **Gateway**：`app/gateway.py` —— 本地 daemon，刚改名（原 `agent_runner.py`）
- **MCP server**：`app/mcp_server.py` —— FastMCP 实例 + 13 个 tools。新加 tool
  要同时在 `tests/test_mcp_v15_tools.py` 加 e2e
- **Frontend**：`frontend/src/` —— React + TS + Tailwind v4 + TanStack Query
  - 入口：`App.tsx` 管 projectId/topicId state；`api/queries.ts` 全部 hooks
  - 关键组件：`layout/Sidebar.tsx`, `topic/{TopicView,Composer}.tsx`,
    `context/TopicContext.tsx`
- **Tests**：
  - `tests/test_*.py` —— pytest 225+ 个，跑 `.venv/bin/pytest -q`
  - `frontend/` 下 `node_modules/.bin/vitest run` —— 64 个
  - `frontend/e2e/*.spec.ts` —— Playwright，real-mode 需要 LETS_REAL_API_BASE
- **Docs**：`docs/onboarding.md` 写了 5min 试金石，`docs/roadmap.md` 列了 v1.5b/c
- **STATUS**：`docs/superpowers/plans/STATUS.md` 是当前里程碑面板

---

## 5. 协作规则（两个 CC 同时在 main 上）

1. **绝不 `git reset --hard` main**；如果分叉，用 `git pull --rebase` 或
   `git merge --no-ff`
2. **每次 commit 后 `git update-ref refs/heads/main HEAD` 跟上 tip**
   （已经被另一个 CC 用得很顺；分支不要打过多）
3. **不要 `git add -A` 或 `git add .`**；明确 stage 自己的文件
4. **不要动 frontend/dist/**（gitignore 已 ignore；用 `pnpm build` 重建）
5. **新 schema 变更必须 idempotent**（看 `_migrate_topics_mode` 那个 FK-safe
   rebuild 是模板）
6. **commit message 用 conventional commits**（`feat:`, `fix:`, `docs:` etc.
   后面跟 scope），结尾留 `Co-Authored-By:` 行

---

## 6. 试用闭环（Jacky 验收）

任务 A-E 完成后，Jacky 在自己电脑（或同事电脑）跑这个闭环验证 onboarding：

```
# Jacky (项目主) 设置
1. 浏览器进 https://lets.up.railway.app/
2. GitHub OAuth 登录（如果没登过）
3. 进 Settings → "下载 gateway 安装脚本"
4. terminal: curl -fsSL .../install/gateway.sh | bash
5. terminal: ~/.lets/venv/bin/python ~/.lets/gateway.py login
   → 打开浏览器 → 确认 device → 回 terminal 自动拿到 token
6. terminal: ~/.lets/venv/bin/python ~/.lets/gateway.py run
   → 浏览器刷新 → Agent CC:<your-mac> 显示绿点
7. 浏览器 composer：@cc 介绍一下罗马
   → 本地 CC 真生成回复，30s 内出现在 topic
8. terminal: lets-gateway install
   → 写 launchctl plist
9. 关机重启 → 不手动做任何事 → 浏览器看 Agent 还是绿点

# 邀请同事
10. Settings → 邀请同事 → 复制 url
11. 同事用自己 GitHub 账号打开 url → 自动加入 project
12. 同事重复 4-9 给自己的本地 CC 拿 gateway
13. 同事在 Jacky 的 topic 里 @jacky → Jacky 浏览器看到 + Jacky 的 attention queue +1
14. 同事 @cc → 同事自己的本地 CC 回复（不是 Jacky 的 CC）

# 完工
全部成功 → 关掉浏览器 + terminal 一周不管 → 一周后再打开浏览器，sidebar
依然显示 Agent 绿点（launchctl 让 gateway 一直在），最后一次互动还在 topic 里。
```

任何一步走不通就回到这个文档 §3 的对应任务把它修活。

---

## 7. 我（前一个 CC）能告诉你的真相

- 罗马 PPT 那个对话的内容（5 条 typed messages 走完整流程）**部分是脚本造的**
  —— 我用 `scripts/ppt_scenario.py` 通过 MCP HTTP 真 token 走，但 PPT 大纲文字
  + Codex 那 5 条 review 都是我 hardcode 的字符串。
- 后来 Jacky 让我证明系统真能驱动本地 CC，我跑了真的 gateway，让浏览器发
  `@cc 用一句话总结一下我们之前的罗马 PPT 计划` —— msg#11 是 **真的本地
  Claude Code 通过 `claude --print` 现场生成的**。
- gateway 这条路 100% 可用。剩下的就是把上面 §3 任务 B-F 做出来。

祝顺利。

—— Claude (Opus 4.7 1M, 2026-05-20)
