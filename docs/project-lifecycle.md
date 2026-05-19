# Project Lifecycle

## 1. 这份文档解决什么

聊出一个想法之后，怎么让它变成一个真实可以多人多 agent 协作的 project？

具体说：
- 几个人在 `#广场` 聊了"我们做个 X 吧"
- 谁来真去 `git init` + `gh repo create`？
- 同事的本机怎么 `git clone`？
- agent 怎么知道 repo 在哪？
- 失败怎么回滚？

本文是 Lets 项目从无到有、从入会到归档的完整生命周期定义。涉及 GitHub OAuth、本地 daemon、`project_proposal` typed message、跨机器同步协议。

## 2. 阶段总览

```
1. 想法触发        (人在 conversation 里说"我们做个 X 吧")
2. 提议           project_proposal typed message
3. 协商           参与者评审 / 修改 / 投票
4. 创建           owner 执行 git init + gh repo create
5. 分发           其他成员本机 daemon 收到并 clone
6. 初始化         .claude/ 骨架 / template 继承
7. 注册           Lets 后端 project 记录
8. 通知           topic 自动切换 / Attention Queue push
9. 进入日常        spec change / Artifact / topic ...
10. 归档 / 关闭    .claude/ 落底 / repo archive / project read-only
```

## 3. 阶段细节

### 3.1 想法触发（无新机制）

人在任何 channel / topic 里聊出"做个 X"。这阶段 Lets 不做任何识别 —— **避免误触发**，等待人显式发起。

### 3.2 提议：`project_proposal` typed message

由人或 agent 主动发出。建议人通过 `/create-project <slug>` slash command 触发，agent 也可以主动 propose 进 Attention Queue。

```
claude·neo-mbp [project_proposal]
  Name:         echomem-demo
  Visibility:   public                          ← public / private / internal
  Owner:        @Neo                            ← GitHub repo 的 owner
  Repo:         jacky-li/echomem-demo
  Members:      Neo (admin), Trinity (write), Morpheus (write)
  Default branch: main
  Local path:   ~/work/lets-projects/echomem-demo  ← 每个成员本机统一路径
  Template:     blank | research-talk | webapp | ...
  Default channels: #广场, #decisions
  
  Inherits spec from (optional): echomem (复用 PPT skill 等)
  
  [Approve as Owner]   [Suggest changes]   [Decline]
```

字段说明：

| 字段 | 必填 | 说明 |
|------|:----:|------|
| Name | ✅ | URL-safe slug |
| Visibility | ✅ | 影响 GitHub repo 可见性 |
| Owner | ✅ | 用 owner 的 OAuth token 创建 repo |
| Repo | 自动 | `<owner-github>/<slug>` |
| Members | 默认 = 当前 topic participants | 列表 |
| Local path | 默认 `~/work/lets-projects/<slug>` | 用户可改 |
| Template | optional | 决定初始 `.claude/` 内容 |
| Inherits spec | optional | 从另一 Lets project 复制 skills / CLAUDE.md |

### 3.3 协商

每位 member 需要 [Approve] 或 [Decline] —— 加入 project 是显式动作，不允许"未读 = 默认加入"。

| 状态 | 进项目? |
|------|:------:|
| Approve as Owner（owner 必须） | ✅ |
| Approve（member） | ✅ |
| Decline | ❌ 不进，但保留对话 |
| 未回应 | ⏸ pending，最多 24h，超时 = Decline |

中间可以 [Suggest changes]：例如改 visibility / template / 加 member。修改后投票重置（已 approve 的 member 需要 re-approve）。

### 3.4 创建：owner 本机执行 git / GitHub 操作

Owner approve 后：

```
[step 1] Owner 本机 daemon 收到 create_project 事件
  ↓
[step 2] 检查 owner 是否绑过 GitHub OAuth
  - 未绑 → 浏览器弹出 OAuth flow（一次性）
  - 已绑 → 继续
  ↓
[step 3] daemon 调用 gh repo create
  gh repo create jacky-li/echomem-demo --public --description "..."
  ↓
[step 4] daemon 在 owner 本机执行
  git clone https://github.com/jacky-li/echomem-demo.git ~/work/lets-projects/echomem-demo
  ↓
[step 5] 添加协作者
  for m in members:
    gh api PUT /repos/jacky-li/echomem-demo/collaborators/<m>
  ↓
[step 6] 应用 template（如有）
  cp -r ~/.lets/templates/<name>/ .claude/
  git add . && git commit -m "init project from template"
  git push
  ↓
[step 7] 通过 Lets 后端广播 project_created 事件
```

**关键技术决定**：
- **OAuth token 不上传到 Lets 后端** —— 留在 owner 本机 keychain（macOS Keychain / Linux secret-tool）；daemon 调用 GitHub API 时用本机 token
- Lets 后端只知道 `project_id ↔ repo_url ↔ member_list`，不知道任何 token

### 3.5 分发：其他成员本机 clone

```
[step 1] Lets 后端广播 project_created 给所有 approved member 的 daemon
  ↓
[step 2] 每个 member 本机 daemon 收到
  - 检查本机是否有 GitHub OAuth（member 自己的 token）
  - 检查 local_path 是否冲突（同名目录已存在）
  - 检查 disk space
  ↓
[step 3] daemon 执行
  git clone https://github.com/jacky-li/echomem-demo.git ~/work/lets-projects/echomem-demo
  ↓
[step 4] daemon 上报 clone_complete + path + git_head 到 Lets 后端
  ↓
[step 5] Lets 后端汇总，达到 quorum（默认全部 member）后标 project = ready
```

**失败处理**：
- Step 2 检查失败 → Attention Queue push（"Trinity 本机磁盘不足，要不要选别的路径？"）
- Step 3 clone 失败（网络 / 权限）→ retry 3 次 → 失败则 Attention Queue 给 owner（"Trinity 加入失败，需要你介入"）
- **不让单个成员的失败 block 整个项目** —— 项目仍然可用，那个成员显示 `pending_clone` 状态，他自己可以稍后重试

### 3.6 初始化：`.claude/` 骨架

新 project 默认的 `.claude/` 结构：

```
<project-root>/
├── CLAUDE.md                      ← 项目背景，team 通过 spec_change 演化
├── .claude/
│   ├── skills/                    ← 项目专用 skills（可继承自 template / 另一 project）
│   ├── commands/                  ← 项目专用 slash commands
│   ├── agents/                    ← 项目专用 subagents
│   └── settings.json
├── .mcp.json                      ← 项目级 MCP server 配置
├── .gitignore                     ← Lets 推荐配置
└── README.md                      ← 自动生成简短介绍
```

**Template 系统**：
- `blank` ：最小骨架
- `research-talk` ：含 PPT skill / 演讲风格 / 文献调研流程
- `webapp` ：含前端 skill / 部署流程 / API 风格
- 用户可以"另存为 template" → 跨 project 复用 spec

### 3.7 注册到 Lets 后端

Lets `projects` 表新增一行：

```
{
  id: prj_xxxxx,
  name: "echomem-demo",
  slug: "echomem-demo",
  github_repo: "jacky-li/echomem-demo",
  visibility: "public",
  owner_human_id: human_neo,
  member_human_ids: [human_neo, human_trinity, human_morpheus],
  member_status: {
    human_neo: { local_path: "~/work/lets-projects/echomem-demo", git_head: "abc123", state: "ready" },
    human_trinity: { local_path: "...", git_head: "abc123", state: "ready" },
    human_morpheus: { local_path: "...", git_head: null, state: "pending_clone" }  ← 个例失败
  },
  default_channels: ["#广场", "#decisions"],
  created_at: ...
}
```

### 3.8 通知：topic 切换 + Attention Queue

成功后：
- 当前 topic stream 出现一条 `[system] project ready · 3 clones synced` 系统消息
- 侧栏新 project 进入"我的项目"列表
- 第一个 topic 自动创建：`#广场` 默认 channel 已开
- Attention Queue 给 owner 一条 "项目就绪，要不要现在跳进去？"（可点击直接进 project view）

## 4. 后续阶段（创建之后）

### 4.1 加入新成员（已有项目）

Owner 或 admin 在项目内发：`/invite @ling`

```
[invite_proposal] · 邀请 @ling 加入 jacky-li/echomem-demo as write
  ling 接受后会：
  - 加入 GitHub collaborators
  - 本机 daemon clone repo
  - 进入 Lets project
  
  [发送给 ling]  [Cancel]
```

ling 收到 DM + Attention Queue 项：
```
[invitation] Neo 邀请你加入 echomem-demo
  Local path: ~/work/lets-projects/echomem-demo（可改）
  
  [Approve & Join]  [Decline]
```

Approve 后流程同 §3.5 step 2-5。

### 4.2 多机器加入（同一人）

Trinity 既在 trinity-air 上用 Lets，也想在 home-desktop 上用：

- home-desktop 装好 Lets installer 后，登录同一账号
- 自动检测到 Trinity 已是某些 project 的 member
- 提示 "你在 trinity-air 上参与了 3 个项目，要在本机 clone 吗？" —— 用户可选 all / select / none
- 每个被选中的项目本机 clone

**关键**：每台机器是独立的 `agent_instance`，对应 product-thesis 里"三段身份"中的 `agent_instance` 层。

### 4.3 跨机器同步状态

Lets `project_member_devices` 表跟踪每个人在每台机器上的状态：

```
{
  project_id: prj_xxx,
  human_id: human_trinity,
  device_id: dev_trinity_air,
  local_path: "...",
  git_head: "abc123",
  agentfs_status: "in_sync" | "pending" | "error",
  last_seen_at: ...
}
```

Project view 的 UI 可以显示："Trinity 在 trinity-air 是 v3 head，在 home-desktop 还是 v2 head" —— 跨设备一致性可观察。

### 4.4 处理 git 冲突 / 跨机器编辑

- Agent 默认在 push 前 `git pull --rebase`
- 冲突时不让 agent 自动 merge —— Attention Queue push 给冲突方："你和 ling 都改了 `.claude/skills/foo/SKILL.md`，需要你 review"
- 提供"看 diff / 选保留哪边 / 手动合并"三选项

### 4.5 归档 / 关闭

```
/archive-project
  确认归档 echomem-demo？归档后：
  - GitHub repo 改为 archived (read-only)
  - Lets project 标 archived
  - 本机 clone 保留，不删
  - Attention Queue 不再 push
  - Topic 进入 read-only
  
  [Confirm]  [Cancel]
```

归档不删除，永久保留为历史。

## 5. OAuth / Token 管理

### 5.1 GitHub OAuth

| 时机 | 触发 |
|------|------|
| 首次创建 project（作为 owner） | 引导 OAuth flow |
| 加入别人创建的 project | 引导 OAuth flow（如未绑） |
| Token 过期 / 撤销 | Attention Queue push："你的 GitHub 授权过期，重新登录" |

**Scopes 最小化**：
- `repo` （创建 / push / pull private repos）
- `read:user`
- 不要 `admin:org` / `delete_repo` 等危险权限

### 5.2 Token 存储位置

- **不上传到 Lets 后端**
- macOS：Keychain
- Linux：libsecret / pass
- Windows：Credential Manager

本机 daemon 调用 GitHub API 时从本机 keychain 取 token。

### 5.3 后端如何识别用户

不靠 token，靠：
- Lets 自己的 session（用户登录 Lets 网站后 cookie）
- daemon 启动时携带 device-specific token，跟 Lets 后端建立长连接（WebSocket / SSE）
- 后端通过 device token 知道"这台机器是 Trinity 的 trinity-air"

## 6. 失败模式与回滚

| 失败 | 影响 | 回滚 |
|------|------|------|
| Owner GitHub OAuth 失败 | 整个 project_proposal 失败 | 提议保留为 draft，可重试 |
| `gh repo create` 失败（如 slug 冲突）| Owner 本机 daemon 提示选别的 slug | 自动 retry 一次（加 -2 后缀），仍失败则 push Owner |
| `git clone` 失败（owner）| project 不创建 | 完全回滚 |
| `git clone` 失败（某 member）| project 仍创建，那个 member 状态 = pending_clone | 该 member Attention Queue + 重试入口 |
| Add collaborator 失败 | project 创建但 member 无 git 访问 | Attention Queue：手动 invite |
| Network 断 | daemon 缓存 pending action，恢复后重放 | 自动 |
| 不同 member 本机 path 冲突 | 该 member daemon 报错 | 提示选另一 path |

## 7. 跟其它文档的关系

- `product-thesis.md`：定位（"Agent Spec 协同"是核心，project 是承载 spec 的容器）
- `agent-spec-collaboration.md`：项目级 spec 走 Git，本文负责"Git repo 怎么从无到有"
- `onboarding.md`：第一次创建 project 是 onboarding 的一部分
- `artifact-sync-strategy.md`：project 内 Artifact 同步走不同 backend，本文管 project 这一层
- `roadmap.md`：本文涉及的能力在 v1.5a / v1.5b

## 8. Open Questions

1. **Org 化 project**：当前假设 owner 是个人 GitHub 用户。如果 team 有 GitHub Org，project 用 Org repo（如 `lets-team/echomem-demo`）？建议 v1.5 支持但不强制，owner OAuth 时可选择"个人账号 / 加入的 org"
2. **私有 GitHub Enterprise**：用户的 GitHub 不是 github.com，是 GHE？v2 评估
3. **GitLab / Gitea backend**：纯 Git 路径理论上可替换，但 Lets v1.5 锁 GitHub
4. **没有 GitHub 账号的成员**：朋友 / 非工程师没注册 GitHub？短期答案：必须有；中期可考虑"semi-member"模式（只用 Lets web，不参与 git）
5. **Lets 自己的 project 元数据**（不在 GitHub repo 里的部分，如 message stream）：存哪？答：Lets 后端 Postgres（不在用户 repo 里）
