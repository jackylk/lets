# Workspace 分层 + 成员制 + 邀请 — 设计方案

**日期**: 2026-05-21
**作者**: jacky (与 Claude 协同)
**状态**: 待实现

## 1. 背景

当前 Lets 的左侧菜单只有「话题」一层（数据上是 `topics` 表）；表面上代码里有 `ChannelRow` 等"channel"字样，但 channel 不是真实概念，只是命名残留。

后端有 `projects` 表作为顶层容器，但前端没有 switcher UI——所有用户、所有 topic 共用一个隐藏的 `default` project。`agent_instances` 挂在 `humans` 上，topic 对整个 instance 全局可见，没有任何 ACL/邀请机制。

这次设计要解决的是：

1. **给 topic 一个分组层**——一个用户做多个方案时能切换、不互相干扰
2. **支持多人协作**——把别人拉进来一起设计同一个方案
3. **支持多 agent 参与**——agent 是工作区的 first-class 成员，多个人都能 @ 它、看它的回复
4. **保留"开箱即聊"体验**——新用户登录后不需要建任何东西就能开始

## 2. 命名与定位

- 分组层叫 **工作区 / workspace**（中文 UI label "工作区"）
- 不叫 channel（IRC 风格、太聊天）、不叫 project（已经被代码占用，并且过重）
- 一个 workspace 对应**一个方案 / 系统 / 模块**的设计讨论容器
- 例子：用户认证方案、API v2、权限系统、支付链路、数据建模

## 3. 数据模型

复用现有 `projects` 表的语义，**重命名为 `workspaces`**（schema 重写，因为没真实用户）。

### 3.1 表结构

```sql
-- workspaces: 工作区，一个方案 / 系统 / 模块
CREATE TABLE workspaces (
    id BIGSERIAL PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    owner_human_id BIGINT NOT NULL REFERENCES humans(id),
    is_private BOOLEAN NOT NULL DEFAULT TRUE,  -- v1 全 true，留口子
    deleted_at TIMESTAMPTZ,                    -- 软删
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- topics: 话题，挂在工作区下
ALTER TABLE topics RENAME COLUMN project_id TO workspace_id;
-- 其他列不变

-- workspace_members: 人成员
CREATE TABLE workspace_members (
    workspace_id BIGINT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    human_id BIGINT NOT NULL REFERENCES humans(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('owner', 'member')),
    joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (workspace_id, human_id)
);

-- workspace_invites: magic link
CREATE TABLE workspace_invites (
    id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    token TEXT UNIQUE NOT NULL,
    created_by_human_id BIGINT NOT NULL REFERENCES humans(id),
    expires_at TIMESTAMPTZ,    -- NULL = 永不过期 (v1)
    max_uses INT,              -- NULL = 无限次 (v1)
    used_count INT NOT NULL DEFAULT 0,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- agent_instances: agent 直接挂工作区
ALTER TABLE agent_instances ADD COLUMN workspace_id BIGINT NOT NULL REFERENCES workspaces(id);
-- human_id 保留语义改为"启动者"（提供算力/token），不再代表归属
```

### 3.2 关键约束

- 一个 human 可以同时是多个 workspace 的成员
- 一个 agent_instance 只属于一个 workspace（想跨 workspace 就再启一个）
- 一个 workspace 至少有一个 owner（删 owner 前必须转移）
- topic 必须挂在 workspace 下，无悬空 topic
- caller 必须是 workspace 成员才能列出/查看该 workspace 的 topic
- ChannelRow 等 channel 命名残留同步清理为 TopicRow

### 3.3 初始化 / 迁移

由于现在没真实用户：

```sql
TRUNCATE topics, projects, agent_instances, ... CASCADE;
-- 然后按新 schema 重建，不写迁移脚本
```

新用户首次登录走 onboarding 流程自动建工作区+默认 topic（见 §5）。

## 4. API

| Method | Path | 说明 | 权限 |
|---|---|---|---|
| GET | /api/workspaces | 列出 caller 作为成员的工作区 | 登录 |
| POST | /api/workspaces | 创建工作区（caller 自动 owner） | 登录 |
| GET | /api/workspaces/:id | 获取单个工作区 | 成员 |
| PATCH | /api/workspaces/:id | 重命名 | owner |
| DELETE | /api/workspaces/:id | 软删（设 deleted_at） | owner |
| GET | /api/workspaces/:id/topics | 列出工作区下话题 | 成员 |
| POST | /api/workspaces/:id/topics | 创建话题 | 成员 |
| PATCH | /api/topics/:id | **新增** 改 workspace_id 实现跨域移动 | from + to 都是成员 |
| GET | /api/workspaces/:id/members | 成员列表（含 agents） | 成员 |
| DELETE | /api/workspaces/:id/members/:human_id | 移除成员 | owner |
| POST | /api/workspaces/:id/invites | 生成 magic link | owner |
| GET | /api/workspaces/:id/invites | 列出有效邀请 | owner |
| DELETE | /api/invites/:id | 撤销邀请 | owner |
| POST | /api/invites/:token/accept | 接受邀请 | 登录 |
| GET | /join/:token | magic link landing page | 公开 |

**device-flow 改动**: `POST /api/auth/device-flow/start` 新增可选参数 `workspace_id`。agent 注册到该 workspace。未传时落 caller 默认 workspace（首个 owned 的）。

## 5. 新用户开箱即聊

1. 用户 GitHub OAuth 登录 → 后端 upsert `humans` 行
2. **第一次登录时自动建立**：
   - 一个 workspace：`name='我的工作区'`, `slug='my-workspace-<human_id>'`, `owner=self`
   - 一行 `workspace_members(role='owner')`
   - 一个 topic：`title='主频道'`, `slug='general-<ts>'`, 挂在该 workspace 下
3. 前端首次加载发现已有 topic → 直接进入聊天界面

→ 用户视角：**登录后直接看到聊天框**，无任何配置步骤。

## 6. UI 设计

### 6.1 Sidebar 布局（混合模式）

```
┌─────────────────────────────────┐
│ 我的工作区 ▾  用户认证 │ API v2 │+ │  ← 顶部 segmented switcher
├─────────────────────────────────┤
│ 话题            4    ＋          │
│  TOPIC1  OAuth 流程             │
│  TOPIC2  Token 刷新机制         │
│  TOPIC3  权限模型               │
│  TOPIC4  Rate limit 设计        │
├─────────────────────────────────┤
│ ▸ 用户认证      6                │  ← 其他 workspace 折叠
│ ▸ API v2        3                │
│ ＋ 新建工作区                    │
├─────────────────────────────────┤
│ 成员                            │
│  YOU      owner                 │
│  alice                          │
│  claude   agent · alice 启动    │
│  ＋ 邀请成员                     │
└─────────────────────────────────┘
```

- 顶部 switcher 显示当前 + 最近活跃的 2 个 workspace + 创建按钮
- 当前 workspace 的 topic 展开
- 其他 workspace 作为折叠 section 列在下方
- 末尾"+ 新建工作区"
- "Agent" section 并入"成员"，因为 agent 现在跟人平级

### 6.2 创建工作区

点 `+` → inline 浮出输入框 → 只填名字 → Enter 提交 → 后端生成 slug → 返回新 workspace → 前端切到新 workspace。

**Slug 生成规则**：
- ASCII 名字：小写 + 空格转 `-` + 去除非 `[a-z0-9-]` 字符
- 含 CJK / 非 ASCII：fallback 为 `ws-<6位随机base32>` （例：`ws-h4k2qm`）
- 冲突时追加 `-2`、`-3`…

避免在 URL/CLI 里塞 percent-encode 的中文。

### 6.3 邀请流

owner 点"邀请成员"→ 弹 dialog：

```
邀请新成员加入「我的工作区」

把这个链接发给 ta：
┌──────────────────────────────────────────┐
│ https://lets.app/join/a8f3kxq2  [复制]    │
└──────────────────────────────────────────┘

收到链接的人点击进入，登录 GitHub 后会自动成为成员。
                                       [完成]
```

Bob 收到链接 → 点击 → `/join/:token`：
- 未登录 → 跳 `/login?redirect=/join/:token`
- 登录后 → 后端 POST `/api/invites/:token/accept` → 加入 workspace → 跳到该 workspace 的默认 topic
- 已是成员 → 直接跳进去，不重复加成员行

v1 邀请永不过期、无限次（schema 已留 `expires_at` / `max_uses` 字段，UI 不暴露）。

### 6.4 跨工作区移动 topic（v1 最小）

topic 设置面板（或标题旁的省略号菜单）加"移动到..."下拉：
- 列出 caller 是成员的所有 workspace
- 选定后 PATCH topic.workspace_id
- 右键 / 拖拽 v1 不做（next iteration）

### 6.5 Agent 启动（CLI）

```bash
# 默认进 caller 的默认工作区（my-workspace）
lets add claude

# 加入指定工作区
lets add claude --workspace user-auth
```

device-flow 携带 `workspace_id`。gateway 启动 agent 时把 `agent_instances.workspace_id` 写入。该 workspace 的所有成员都能 @ 它、看到它的回复。

同一台机器跑多 workspace 的 agent：多次 `lets add --workspace X`。

## 7. 边缘情况

| 情况 | 行为 |
|---|---|
| Owner 删除工作区 | `deleted_at` 打时间戳；topic/成员/邀请/agent_instances 行不级联删，只是隐藏。v1 不做恢复 UI，v2 加 |
| Owner 删自己唯一工作区 | 禁止（保证用户至少有一个能聊） |
| Owner 转移 | v1 不支持。owner 退出团队的能力延后 |
| Owner 退出 GitHub 登录 | 已挂的 agent 仍跑（行还在），其他成员仍能看 |
| 一人多 workspace 成员 | 支持。sidebar 同时展示，顶部 switcher 切换 |
| 跨 workspace 移动 topic | 要求 caller 是 from + to 双成员；不通知；历史保留 |
| Magic link 撤销后 | 已加入的成员不踢；新点击的人被拒绝 |
| Agent 启动者不在工作区 | agent 仍可参与（agent 是 workspace 成员，与启动者解耦）|
| 第一次登录前已有 magic link | 走 magic link 接受流程后再触发"开箱即聊"自动建工作区（用户至少有自己 owned 的工作区 + 被邀请的工作区）|

## 8. 实现拆分

按依赖顺序：

1. **Schema 重写 + 数据清盘**
   - `app/db.py` 重写表定义
   - 删 `lets.db.bak-1779347791` 之类残留备份
   - Postgres 数据库 truncate 重建

2. **后端 API 层**
   - workspace CRUD
   - 成员校验中间件（topic / message / artifact API 全部加成员校验）
   - 邀请 token 生成 / accept
   - device-flow 加 workspace_id 参数

3. **CLI / gateway**
   - `lets add --workspace <slug>` 参数
   - gateway 把 workspace_id 写入 agent_instances

4. **前端 sidebar 重写**
   - 顶部 switcher
   - 嵌套折叠 section
   - 创建 workspace inline 输入
   - 成员列表合并 agent

5. **新用户 onboarding**
   - 后端首次登录自动建 workspace + 默认 topic
   - 前端去掉"主频道" auto-create（搬到后端）

6. **邀请 UI**
   - 邀请 dialog
   - `/join/:token` 落地页

7. **跨域移动 topic**
   - topic 设置下拉

8. **命名清理**
   - `ChannelRow` → `TopicRow`
   - CSS / 注释中 channel 残留

## 9. 测试要点

- workspace 成员校验：非成员 GET topic 列表返回 403
- 邀请 accept：重复 accept 幂等，不重复加成员
- magic link：未登录跳 login 后还能回 `/join/:token` 继续
- topic 跨 workspace 移动：caller 不是 to-workspace 成员 → 403
- agent 启动 device-flow：未传 workspace_id → 落 caller 默认 workspace
- 新用户首次登录：自动落到一个新建 workspace 的默认 topic
- 删 workspace：topic / 邀请被隐藏，访问 GET 该 workspace 返回 404

## 10. 显式 non-goals (v1 不做)

- workspace 公开/私有切换（schema 留口子，UI 不做）
- workspace owner 转移
- 删除后恢复 UI
- magic link 过期 / 限制次数（UI 不暴露）
- 右键菜单 / 拖拽 topic
- agent 跨 workspace 共享
- 成员角色细分（只有 owner / member 两档）
- "@ 提及" 高亮 / 通知
- 通过 GitHub 用户名预邀请
