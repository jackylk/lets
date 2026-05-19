# Product Thesis

> **Revision 2026-05-19** —— 经过一系列产品讨论和业界对照（Slock / Multica / Wanman），本份 thesis 经过较大调整。核心更新：
> - 定位从 "Agent-native R&D workspace" 升级为 **"conversation-driven agent spec collaboration"**
> - **Agent Spec 协同 + 版本化** 成为第 0 差异化（最核心）
> - **Artifact-driven conversation** 成为产品形态主轴
> - **目标分解 + 守住焦点（nudge）** 成为 agent 主动性的第一个落地点
> - v1.5 第一推广场景从"代码"切换为 **PPT 协作**
> - 引入 **agent 主动性 L0–L3 layers** 路线
> - 允许 **单人也能用**，但 2+ 人是核心 wedge

## 1. Product

**Lets** ——
**"和人聊一聊，让 agent 把想法做出来给大家看；同时让团队所有人的 agent 行为保持一致。"**

英文：**Conversation-driven agent spec collaboration, with humans and agents around the table.**

一个 web 协作工作台，把团队（哪怕只有一个朋友）和他们的本地 agent (Claude Code / Codex / ...) 放进同一个 conversation surface，围绕 Artifact 协作，并把所有 agent 的 spec（skills / CLAUDE.md / MCP / commands）作为团队共享 + 版本化的对象统一演化。

## 2. One-line Positioning

> Humans 一起聊一聊，agent 把想法做成 Artifact 给所有人看，过程产生的 spec 改动（skill / 规则 / 模板）被团队评审、版本化、自动同步到所有人本地的 agent。

不是又一个 agent IDE。不是又一个 chat UI。是 **"Git for agent spec + Chat for collaboration + AgentFS for the things git can't"**。

## 3. Scope and Users

### 3.1 适用规模

| 规模 | 是否能用 | 价值密度 |
|------|:--------:|:--------:|
| 单人 + N agent | ✅ 能用 | △ 中（跟 Cursor / Claude Code 互补） |
| **2-8 人小团队 + 各自 agent** | ✅ 核心 wedge | ✅✅ 高 |
| 跨组织 / 大企业 | △ v3+ 才考虑 | — |

**Wedge 在小团队**（2-8 人），但产品**不强制要 2+ 人**才能注册即用。"邀请同事"是 onboarding 引导而非门槛。

### 3.2 适用场景

| 场景类别 | 阶段 | 例子 |
|---------|------|------|
| 软件 R&D 协作（工程师团队） | v1.5 dogfood + 内部场景 | 多 agent 写代码 / review / 决策 |
| **PPT / 文档 / 报告 协作**（工程师 + 非工程师） | **v1.5 第一推广场景** | 季度回顾 PPT / 客户提案 / 技术分享 / 演讲稿 |
| 数据分析 / 决策辅助 | v2 | 对比方案 / 跑数据 / 出报告 |
| 家庭 / 教研 / 运营场景 | v3 | 选学校 / 备课 / 客户旅程分析 |

**关键决定**：v1.5 主推 PPT 协作作为第一对外案例，理由：
1. 高频（白领每月几次，开发者每月 < 1 次新 feature）
2. 同事 + 朋友都能用，TAM 大
3. 价值可视化（PPT 缩略图 > 代码 diff）
4. 时间短（一个 PPT 几小时，一个 feature 几天）
5. 程序员讨厌做 PPT，Lets 对工程师团队也是高价值

### 3.3 用户的本地环境前提

**至少一台机器装了 Claude Code / Codex CLI**（短期内是硬门槛）。非工程师朋友可以靠"工程师朋友帮装"、纯 web 端只读 + 评论。

未来可能引入 hosted agent 解锁纯 web 端用户，但**当前坚定走"协调本地 CLI agent"路线**，不自带 LLM runtime。

## 4. Problem

业界产品各自解决了片段，没有人解决整条流：

| 产品类别 | 已解决 | 未解决 |
|---------|--------|--------|
| GitHub / Linear | 代码 / 工单 | 多人多 agent 实时协作；agent spec 同步 |
| Cursor / Claude Code / Devin | 单人 agent 编码 | 多人协作；非代码 Artifact；agent 行为一致 |
| Slock | 多人多 agent chat | agent spec 协同 / 版本化 |
| Multica | issue 分派给 agent | conversation-driven；非代码场景；spec 协同 |
| Wanman | autonomous 多 agent | human-in-the-loop；多人 |
| ChatGPT Canvas / Claude Artifacts | 单人 + AI 产 Artifact | 多人围 Artifact 讨论 |
| Tome / Gamma / Lovable | AI 生 Artifact | 多人协同；spec 一致；本地 agent |
| Figma | 多人 Artifact | agent 参与；spec 协同 |

**完整闭环没有人做**：
- 多人 + 多 agent
- 围绕 Artifact 协作
- 同时演化 agent spec
- 移动办公（mobile-first）
- 本地 agent + 远程协作

## 5. Key Differentiators

差异化按重要性排，**#0 最核心**：

### #0. Agent Spec Collaboration（最强护城河）

团队的 agent 行为一致性 —— skills / CLAUDE.md / MCP configs / commands —— 通过 conversation-driven UI 协同演化，自动版本化，可回退。

- 工作流：聊出 spec 需求 → agent 起草 → 团队评审 → Approve → 自动 commit 到 Git → 同事 agent 自动同步
- 视觉：`spec_change` typed message，带 diff 预览和投票 bar
- 底座：项目级 spec 走 Git，全局个人 spec 走 AgentFS（dbay-fuse 已可用）

详见 `docs/agent-spec-collaboration.md`。

**业界没有任何产品做这层。**

### #1. Artifact-driven Conversation

产品的产物不是 chat log 本身，是 **Artifact**：PPT / 报告 / 原型 / 网页 / 分析对比表 / 代码 PR。Topic 进展 = Artifact 演化。

- 每个 topic 通常孕育至少一个"活的 Artifact"
- Artifact 有版本（v0 → v1 → ... → final），可对比、可回退、可 fork
- `artifact_revision` typed message：每次 agent 产出新版本，stream 里出现一条带 inline 预览的卡片
- Context pane 始终显示当前 topic 的 Artifact + 版本切换

**业界做这件事的（ChatGPT Canvas / Claude Artifacts / Gamma）都是单人产品**。Lets 的 Artifact 是多人 + 多 agent 围着改。

### #2. Goal Guardian（目标守护 + 偏题提醒）

每个 topic 有 goal + 目标分解树。agent 监听对话流，发现连续偏离当前 active 任务时温和提醒（不强制、不删聊天、给"独立成新 topic"的出路）。

- `task_tree_proposal` typed message：agent 主动提议初始任务分解
- `nudge` typed message：偏题超 5min + 连续 3 条不相关时温和提示
- Context pane 永久显示"目标分解"区，active 任务高亮

**Otter / Krisp 会议笔记工具事后总结，Lets 实时提醒**。业界没有产品做实时聚焦。

### #3. Unified Conversation Surface

人 + agent 在同一个 conversation surface（topic / channel / DM）协作，不用在 N 个 CLI 之间切。

- 主形态：**topic-first**（每个 work item / Artifact 一个 thread）
- 辅助：少量项目层级 channel（`#广场` / `#decisions`）
- DM：1:1 跟 agent 或人

### #4. Mobile-first Attention Queue（S6 异步移交）

打开 app 第一眼不是 channel 列表，是 **"过去一夜，4 件事在等你"**。

- 三组归类：需要决定 / 等你 review / 同事移交
- 每张卡两个 quick action（thumb-up / thumb-down 级别）
- 桌面 + 手机响应式同款体验

**Slock / Multica / Wanman 都没做 mobile**。这是 Lets 区别于"IDE-bound agent"产品的真正护城河。

### #5. R&D Chain inside Exploratory Topics

对软件 R&D 团队（你的 dogfood 场景），保留 `goal → initiative → hypothesis → evidence → decision` 链作为 **exploratory topic 的内部演进结构**。一般 topic 不强制走，但 R&D 主线 topic 自然落到这条链上。

详见原 §6.

### #6. GitHub Completion

代码仍然通过 commit / PR / review / merge / CI 落地。Lets 不重造源代码控制，而是把 PR 视为 Artifact 的一种、把 commit 关联到 task tree 节点。

## 6. Topic Mode: exploratory vs actionable

避免过早分类（issue / idea / 需求 / 痛点 / 技术挑战 ...），只保留**最小硬区分**：

| Mode | 含义 | Agent 默认工作方式 |
|------|------|-------------------|
| `exploratory` | 还在探索什么是对的问题 | research-first：调研、找资料、提案 |
| `actionable` | 已经知道要做什么 | execution-first：claim、实现、PR |

其他维度走 **tags**（软分类，可后加）：`bug` / `feature` / `research` / `proposal` / `analysis` / `talk-prep` 等。

R&D 链 (`goal → initiative → hypothesis → ...`) 是 **exploratory topic 演进到深度时的内部结构**，不是强制 ontology。

## 7. Agent Proactivity Layers

agent 主动性的演进路径：

| 层 | Agent 做什么 | 谁触发 | 谁决定 | 时机 |
|----|------------|--------|--------|------|
| **L0 Reactive** | 等人派活，干完汇报 | 人 @mention | 人 | ✅ v1.5 |
| **L1 Observer** | 盯内部事件（CI / git / metric / 同事消息），重要时 push | 系统事件 | 人 | v2 |
| **L2 Proactive Researcher** ⭐ | 盯外部环境（论文 / 新闻 / 客户反馈），定期主动产 Artifact | 时间触发 + 长期目标 context | 人 | v2 |
| **L2 Goal Guardian** | 守住对话焦点，偏题时温和 nudge | message 流监控 | 人（可关闭 / 略过） | **v1.5（与 L2 Researcher 同级）** |
| **L2 Proactive Initiator** | 基于观察自己创建 topic / 起草 PR / 加进 Attention Queue | agent 自己判断 | 人（review） | v3 |
| ~~L3 Autonomous~~ | agent 自己拍板自己执行，人退到旁观 | agent | agent | **当前先不加**（这是 Wanman 的赛道；不是绝对不走，但不是 v1.5/v2/v3 的方向）|

**人始终是 final approver**，Lets 的 agent 永远不会"自动 commit、自动 ship、自动 send"。

## 8. Why DBay Matters

单 agent 的记忆可以靠本地 markdown。多 agent + 多人协作不行 —— 需要：

- 并发写
- 共享可见性
- 跨设备同步
- 访问控制
- 分支感知状态
- 版本化 / 回退
- 跨 agent 共享 memory（Claude / Codex 看到同一份记忆）

DBay 因此应从 "memory store" 演进为 **"collaborative state substrate"**。

dbay-fuse 已经提供了 **AgentFS** —— FUSE 接管 `~/.claude/{CLAUDE.md, memory, projects}`，由 outbox + 异步上传 → DBay Postgres。Lets 在 git 之上 + AgentFS 之下，是 conversation-driven 的协作层。

详见 `docs/agent-spec-collaboration.md` §5。

## 9. Product Architecture Layers

```
┌─────────────────────────────────────────────────────────┐
│ Experience Layer                                         │
│   Conversation · Blackboard · Attention Queue · Board   │
│   Artifact view · Spec view · Task tree                  │
├─────────────────────────────────────────────────────────┤
│ Domain Layer                                             │
│   Coordination · Research · Evidence · Spec collab       │
├─────────────────────────────────────────────────────────┤
│ Shared State Layer (Lets's substrate)              │
│   Typed messages · Event log · Identity (3-tier)         │
│   Branch-aware state · Promotion · Presence              │
├─────────────────────────────────────────────────────────┤
│ Integration Layer                                        │
│   HTTP MCP · Local daemon · GitHub · AgentFS · benchmark │
└─────────────────────────────────────────────────────────┘
```

底层 Shared State 由 Lets 后端 + DBay 共同实现。Integration Layer 是边缘连接器。

## 10. Initial Success Criteria

### v1.5 User Value
- 团队（2-3 人）用 Lets 协同完成一份**真实可交付的 PPT**
- 同一份 spec change（skill 改动）在所有人本地的 agent 自动生效
- 一个人通勤时（手机上）能完成 5 个 agent 提案的 review
- 偏题被 agent 提醒时，用户感觉"恰到好处"而不是"烦"

### v1.5 System Value
- 项目级 spec 通过 Git 协同稳定运行
- 个人跨设备同步（AgentFS personal base）跑通至少 1 个 dogfood 用户
- HTTP MCP 让同事的 CC / Codex 远程接入 Lets 后端
- 11 种 typed message 在生产环境无类型混乱

## 11. Strategic Moat

不是更好看的 dashboard，是**累积的 graph**：

- 团队的 Agent Spec 演化历史（哪些 skill 改了为什么改）
- 每个 topic 的 Artifact 版本链
- 跨人 + 跨 agent 的 conversation history
- L2 Proactive agent 累积的"外部信号 → 内部洞察"映射
- R&D 团队的 goal → evidence → decision 链

这 graph 越用越值钱，因为它是 **"团队怎么思考 + 怎么改主意"** 的客观记录，不是任何 IDE / chat / project management 工具能提供的。

## 12. Anti-goals (明确不做)

1. **不自带 LLM runtime** —— 用户用本地 CC / Codex / 其他 CLI
2. **不重造文件格式** —— 直接用 Claude Code / Codex 已有的目录结构
3. **不重造版本控制** —— Git 是底座
4. **不重造 IDE / 编辑器** —— Cursor / VS Code 仍是写代码的地方
5. **不替人决策** —— agent 永远不自动 commit / send / publish
6. **不强迫用户暴露所有 `~/.claude/`** —— 个人空间不被团队侵入
7. **不在 v1.5 / v2 走 autonomous 多 agent 赛道**（保留长期可能性，但当前 wedge 是 human-in-the-loop）
8. **不做企业级权限 / 大组织协作**（v1.5 / v2 / v3 都不做，留给后续）
