# Agent Spec Collaboration

## 1. 为什么这层是 Lets 的核心差异化

回顾业界产品（slock / multica / wanman / cursor / claude code / devin / manus）：

| 产品 | 人 + agent 协作 | **Agent Spec 协同 + 版本化** |
|------|:--------------:|:---------------------------:|
| Slock | ✅ | ❌ |
| Multica | ✅ | ❌ |
| Wanman | △ | ❌ |
| Cursor / Claude Code | △（单人） | △（有 CLAUDE.md 但没团队 UX） |
| GitHub Copilot Workspace | △ | ❌ |
| Devin / Manus | △ | ❌ |
| **Lets** | ✅ | ✅✅ |

**没有任何产品做团队级的 Agent Spec 协同管理**。这比"人和 agent 在 web 上聊天"更核心 —— 因为：

- 聊天和 Artifact 是产品的**表层**
- Agent Spec 是产品的**底层** —— 它决定了团队的 agent 行为是否一致、产出是否可预期

Lets 的 slogan 可以写成：

> **"Conversation-driven agent spec collaboration, with humans and agents both around the table."**

> **"用聊天的方式协同地演化一个团队的 Agent Spec。"**

## 2. 三个层次：Configuration / Context / State

| 层次 | 含义 | 例子 | 团队是否应统一 |
|------|------|------|---------------|
| **Agent Spec**（配置 + 上下文） | agent 怎么工作 + 知道什么 + 信奉什么 | skills · CLAUDE.md · MCP · slash commands · style guide | ✅ **要统一** |
| **Agent State**（运行态） | agent 当下在做什么 | 当前 claim 的 work · 短期 buffer · session history | ❌ 个人的 |
| **Agent Identity** | agent 是谁 | role · instance · device | △ 角色统一，实例区分 |

本文聚焦 **Agent Spec**。

## 3. 两层 Spec —— 对应两条协同路径

Claude Code 的实际配置分两层（其他 CLI agent 类似）：

### 3.1 项目级 Spec

位置：项目根

```
<repo>/
├── CLAUDE.md                      # 项目背景、约定、风格
├── .claude/
│   ├── skills/                    # 项目专用 skill（如 PPT 风格 skill）
│   ├── commands/                  # 项目专用 slash command
│   ├── agents/                    # 项目专用 subagent
│   └── settings.json              # 项目级 settings
└── .mcp.json                      # 项目专用 MCP server 配置
```

**特征**：
- ✅ 天然适合 Git 版本化
- ✅ 团队 clone 即获得，自动一致
- ✅ Per-project 边界清晰：不同项目可以有不同 PPT 风格 / 不同 code review 严格度
- ✅ 不污染个人空间

### 3.2 全局 Spec

位置：用户主目录

```
~/.claude/
├── CLAUDE.md                      # 个人偏好、跨项目指令
├── skills/                        # 全局 skill（跨项目可用）
├── commands/                      # 全局 slash command
├── agents/                        # 全局 subagent
├── settings.json                  # 全局 settings
├── memory/                        # agent 长期记忆
└── projects/<project-id>/         # session history per project
```

**特征**：
- ❌ 不在 Git 里
- ❌ 团队成员各自一份，天然不一致
- 但其中很多内容（个人偏好、个人记忆、session）**本来就不该团队统一**
- 有一小部分（个人跨设备同步 / 跨 agent memory）**需要协同**

## 4. Lets 的官方姿态

**默认引导用户把团队共享的 spec 放项目级**，理由：

1. **可解释性**：每个项目自带 `.claude/`，新人 clone 即知道这个项目用什么 spec
2. **不污染**：你的 PPT skill 不需要存在于无关项目
3. **可版本化**：跟代码一起 commit，回退即 revert
4. **零 FUSE 门槛**：不用装 macFUSE，非工程师友好
5. **Lets 工作**：在 web 上隐藏 git 命令，用户只看"adopt v3"按钮

**反过来：Lets 不应该假设用户的全局 `~/.claude/` 也要团队统一。** 那是个人空间。

但**单用户跨设备 / 跨 agent** 的全局同步，Lets 应该支持 —— 用 AgentFS。

## 5. 三条协同路径

### Path 1：项目级 Spec → Git → Lets conversation-driven UI

**v1.5 主战场，覆盖 90% 团队共享场景**。

工作流：

```
1. 团队成员在 #广场 / topic 内聊：
   "我们应该有一个 PPT skill"
2. Lets 把对话识别为 spec proposal
3. @claude 起草 .claude/skills/team-pptx/SKILL.md
   → Artifact "skill draft v1"
4. 团队评审（message 评论 + 跨成员讨论）
5. claude 迭代 → v2 / v3
6. Decision: adopt v3
7. Lets 自动 git commit + push 到项目 repo
8. 同事的 Claude Code 在下次启动 / 看到 webhook 时 pull
   → spec 在每个人本机生效
9. 一周后发现 skill 产出质量差
   → Lets UI 上"撤销 v3 / 回到 v2"按钮
   → 实际是 git revert + push
```

**关键设计**：
- Lets 在 web UI 上**完全隐藏 git 命令**
- 用户看到的是 conversation + spec card + "adopt / revert" 按钮
- 后台执行的是 git commit / revert / push
- **不依赖 AgentFS、不依赖 macFUSE**

### Path 2：全局 Spec 跨设备同步 → AgentFS Personal Base

**v1.5/v2 引入，单用户跨设备场景**。

这是 dbay-fuse 当前 ONBOARDING 直接覆盖的场景：

```
# 在 jacky-mbp 上
dbay-fuse mount --agent claude &
dbay-fuse takeover --agent claude --nodes CLAUDE.md
dbay-fuse takeover --agent claude --nodes memory
dbay-fuse takeover --agent claude --nodes projects

# 在 jacky-imac 上做同样的事，绑定到同一个 personal base
dbay-fuse agent-bind --agent claude --base personal
dbay-fuse mount --agent claude &
```

**效果**：
- 你的笔记本 + 家里电脑都跑 Claude，看到同一份全局 `~/.claude/`
- 全局 skill / 个人 CLAUDE.md / memory / session history 自动同步
- 没有 git，但有版本控制（dbay-fuse 服务端 PG 表）

**这是单用户场景**，不是团队共享。

### Path 3：跨 Agent Memory 共享 → AgentFS + Memory Derivation

**v2 引入，让 Claude / Codex / OpenClaw 看到同一份长期记忆**。

dbay-fuse roadmap 写明：
- AgentFS → Memory derivation worker
- Virtual CLAUDE.md composition from memory_items
- OpenClaw adapter

这条路径的价值：

```
Claude 在某 topic 上学到一个洞察
   → memory_items 写入 DBay
   → Codex 启动时通过 virtual CLAUDE.md 自动获得该洞察
   → 两个 agent 共享同一份长期记忆
```

**这是 git 做不到的** —— git 没法管 high-frequency 小写 + 跨 agent 自动 derive。

### Path 4：团队级全局 Spec → Team AgentFS Base

**v3 才考虑**。

少数场景：团队共享某个全局 skill（不是项目级）。需要 dbay-fuse 服务端加：
- Team base 概念 + 权限模型
- 多 client 并发写冲突解决
- 强一致性（不能是 eventually consistent）

**不阻塞 v1.5**。等 v1.5 跑通后看用户痛点是否真的在这层。

## 6. 路径选择矩阵

| 场景 | 推荐路径 | 时机 |
|------|----------|------|
| 团队共享 PPT skill / 代码 review 风格 / MCP 配置 | **Path 1**（项目级 Git）| v1.5 |
| 团队共享项目级 CLAUDE.md | **Path 1**（项目级 Git）| v1.5 |
| 个人跨设备同步全局 skill / memory | **Path 2**（AgentFS Personal）| v1.5 / v2 |
| 个人 session history 跨设备 | **Path 2**（AgentFS Personal）| v1.5 / v2 |
| Claude / Codex 共享同一份长期记忆 | **Path 3**（AgentFS + Memory）| v2 |
| 跨设备 + 跨人共享全局 skill（罕见） | **Path 4**（Team Base） | v3+ |

## 7. Lets 在每条路径中的角色

| 路径 | Lets UI |
|------|---------------|
| Path 1 | conversation-driven Git operations · spec card · adopt/revert button · spec change PR-like flow |
| Path 2 | Settings 页一键 "connect to AgentFS personal base" · status 显示 sync state |
| Path 3 | Memory inspector · 看到哪些 memory_items 被哪个 agent 写入 · 谁读了 |
| Path 4 | （v3 设计时再定）|

**核心原则**：Lets 是 conversation surface，git / AgentFS 在它之下做事。用户看的是聊天 + 按钮，不是命令行。

## 8. 版本化与回退

| 路径 | 版本化机制 | 回退操作 |
|------|------------|---------|
| Path 1（Git） | 内建 commit history | `git revert` / branch checkout，Lets UI 触发 |
| Path 2（AgentFS Personal）| dbay-fuse 服务端 PG `agent_files` 表 + version chain | Lets 调 dbay API |
| Path 3（AgentFS + Memory）| memory_items 自带时间戳 | 不"回退"，只是新事实 supersede 旧的 |

**用户视角**：所有路径都暴露同一种 UX —— **"撤销到 v(n-1)" / "切换到 v(m)"**。具体实现差异在底层。

## 9. 反目标（明确不做）

- **不强迫用户把所有 `~/.claude/` 都团队统一** —— 那是个人空间
- **不重造文件格式** —— 直接用 Claude Code / Codex 已有的目录结构
- **不重造版本控制** —— Git 已经在那里
- **不自带 LLM runtime** —— 保持"协调外部 CLI agent"路线
- **不做 autonomous spec evolution**（agent 自己改 spec 自己 commit） —— **人始终是 spec change 的 final approver**

## 10. 跟 PPT 协作场景的关系

PPT 协作（参见 `docs/scenario-pptx.md`）是验证 Agent Spec 协同的最佳场景：

```
人际激发：Neo 在 #广场 说"下周研讨会要讲 agent 记忆"
   ↓
讨论 → Topic 创建：mode=exploratory
   ↓
@claude 起草 PPT 草稿
   → Artifact "ai-memory-talk.pptx v0"
   ↓
迭代：Trinity 反馈 / Morpheus 反馈 → v1, v2
   ↓
发现 spec 问题：现有 research-talk-style skill 字号偏小
   → @codex 起草 SKILL.md 改动（Path 1）
   → Artifact "spec change: skill font 10→14"
   ↓
团队评审 spec change → adopt
   → Lets 自动 git commit → 所有 agent reload
   ↓
用新 skill 重生成 → v3 final
   ↓
若发现 v3 反而变糟 → 一键 revert spec → v2 skill 回归
```

**这个剧本同时验证**：
- ✅ 人际激发 + Artifact-driven（PPT）
- ✅ 多 agent 多人协作（S2 + S3）
- ✅ **Agent Spec 协同 + 版本化**（核心差异化）
- ✅ Spec change 是 typed message（不是隐藏的 git commit）
- ✅ 团队"行为一致性"（PPT skill 改了，所有人 agent 自动同步）

## 11. dbay-fuse 关键集成点

dbay-fuse 当前状态（截至本文）：
- ✅ Passthrough FS / Outbox / Uplink worker（客户端 done）
- ✅ AgentFS HTTP client
- 进行中：DBay 服务端 AgentFS API、memory derivation worker、virtual CLAUDE.md、OpenClaw adapter

Lets v1.5 集成需要：

| 项 | 谁做 |
|----|------|
| Lets 后端能识别用户当前 spec 状态（哪些是 Git-managed / 哪些是 AgentFS-managed） | Lets |
| Lets UI 渲染 spec change diff 预览 | Lets |
| Lets 触发 git commit / revert（封装为 conversation-driven 操作） | Lets |
| Lets 查询 dbay AgentFS 当前 base + sync status | dbay-fuse 提供 API |
| Lets 触发 dbay-fuse takeover / release（option） | dbay-fuse CLI 即可 |

v2 / v3 集成（待 dbay-fuse 服务端 ready）：

| 项 | 谁做 |
|----|------|
| Team AgentFS base 概念 | dbay-fuse |
| 版本化 API | dbay-fuse 服务端 |
| 冲突解决（CAS / CRDT） | dbay-fuse 服务端 |
| 跨 agent memory derivation 看板 | Lets + dbay-fuse |

## 12. 待 close 的开放问题

1. **Lets 是否要内置 git operations**（npm 包嵌入 simple-git？还是依赖系统 git？）
2. **spec change 在 Lets 里的 review UX** —— PR 风格 vs 即时 adopt？建议小改动即时、大改动 PR-like
3. **多人同时改同一个 spec 文件** —— 走 git 路径自然 merge / conflict；UX 上要给"我先看一下 ling 的版本"的入口
4. **agent 自己起草的 spec change 是否需要更严格 review** —— 我倾向"agent 可以提案，但人必须 approve"
5. **AgentFS personal base 在团队场景的角色** —— 用户在 Neo / Trinity / Morpheus 角色下各自有 personal base，互不可见；team-shared 走 Git
6. **跨项目复用 skill** —— 如果某 skill 在多个 Lets 项目都好用，怎么 share？目前答案是"复制到那个项目的 .claude/skills/"；将来可能引入"link to source skill"机制

## 13. 总结一句

> **Lets 不是又一个 agent IDE，是 agent 团队协作的"Git for spec + Chat for collaboration + AgentFS for the things git can't"。**

---

## Track C1 addendum: `project_proposal` typed message

当 Web UI 或某个 agent 在 topic 里提议"开一个新 project"或"重构当前 project 结构"时，它发一条 `project_proposal` typed message 到当前 topic。约定的 shape：

```json
{
  "topic_id": 42,
  "type": "project_proposal",
  "actor_type": "human",
  "actor_id": 7,
  "body": "<短句：rationale>",
  "metadata": {
    "proposed_project_slug": "q3-review",
    "proposed_project_name": "Q3 Review",
    "proposed_repo_path": "/Users/jacky/work/q3-review",
    "rationale": "<更详细的解释，可选>"
  }
}
```

字段说明：
- `proposed_project_slug`（必需）—— 满足 `^[a-z0-9-]+$`，由前端用 `slugify(name)` 生成
- `proposed_project_name`（必需）—— 人类可读名
- `proposed_repo_path`（可选）—— 本地仓库的绝对路径；如果省略则采用 default project 模式
- `rationale`（可选）—— 长理由；`body` 是短句版

**采纳一条 proposal 不是自动的**。流程：
1. 任意成员/agent 发 `project_proposal`
2. 群里讨论；其他人发 `chat` / `question` / `decision` 回应
3. 有人发一条 `type=decision, metadata.decision_type="adopt"` 引用这条 proposal（用 `related_message_ids` 列出 proposal 的 message_id）
4. owner 拿到 adopt 决议后，显式 `POST /api/projects` 创建项目

Track C2 会引入"一步采纳" endpoint（`POST /api/projects/from-proposal/{message_id}`），把第 3 + 4 步合并。在那之前，前端 UI 在 proposal 消息下方显示 "Adopt as new project →" 按钮，跳到新建项目表单（预填 metadata 里的字段），按钮触发的依然是普通 `POST /api/projects`。

**为什么是 typed message 而不是新表**：proposal 本质是讨论的一部分，应该和 chat / question 同流；进决议后才"实例化"成 project 实体。这避免引入"草稿 project"的中间状态。
