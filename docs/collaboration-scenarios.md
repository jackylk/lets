# Collaboration Scenarios

> **Revision 2026-05-19** —— 经过一系列产品讨论，本文经过实质重写：
> - 新增 **S10 Artifact-driven Conversation** 作为统领模式
> - 新增 **S11 Proactive Researcher** 和 **S12 Proactive Initiator**
> - 引入 **agent 主动性 L0–L3 layers** 表
> - 新增章节："PPT 协作 v1.5 标志场景" 和 "目标守护 + 偏题提醒"
> - 修正 S5 措辞：从"永不引入"改为"**当前先不加**"（保留长期可能）
> - 单人也能用 / 2+ 人是核心 wedge 的定位明确

## 1. 为什么这份文档存在

`conversation-layer.md` / `roadmap.md` / `product-thesis.md` 描述了大方向，但不回答一个具体问题：**到底要支持哪些人和 agent 的协作场景？**

不回答，UI 设计会摇摆 —— topic-first 还是 channel-first？Attention Queue 该收什么？mention 怎么路由？目标分解是不是必填？

本文一一列出 Lets 要打透的场景、要支持的场景、要明确不深做的场景，以及每个场景对应的 UI 载体。

## 2. 场景维度

### 2.1 H × A 数量矩阵

```
              1 agent                    N agents
            ┌────────────────────────┬────────────────────────┐
1 human     │ S0  IDE 内 pair        │ S3  一人多 agent       │
            │ Cursor / Devin         │ Fleetify / CliDeck     │
            ├────────────────────────┼────────────────────────┤
N humans    │ S1  多人围攻一 agent   │ S2  多人各自 agent     │
            │ ChatGPT 共享对话       │ Superconductor / Slock │
            │ (业界 demand 弱)       │                        │
            ├────────────────────────┼────────────────────────┤
0 human     │ S4  单 agent async     │ S5  autonomous 多 agent│
            │ Devin background       │ AutoGen / CrewAI       │
            └────────────────────────┴────────────────────────┘
```

### 2.2 时间 / loop 维度

| 同步度 | 含义 |
|--------|------|
| in-the-loop | 每个 agent 动作都需要 human 确认 |
| on-the-loop | agent 自主，human 监督 + 干预 |
| out-of-loop | agent 完全自主，human 只看结果（Lets 当前不打这一格） |

### 2.3 节奏

sync 同步 vs async 异步 —— 跨切上述所有场景。

## 3. Lets 的核心场景

Lets 要打透的核心场景**横跨 H×A 矩阵**：

| ID | 场景 | 为什么对 Lets 关键 |
|----|------|-------------------------|
| **S2** 多人各自 agent | 你和同事各带 agent 协作 | 核心日常 / wedge |
| **S3** 一人多 agent | 你 dogfood 现在的样子 | 入口场景 |
| **S6** 异步移交（mobile） | 睡前丢任务，早上手机看结果 review | **移动办公护城河** |
| **S7** 跨班次移交 | 你下班把 in-progress 交给同事，他下班再交回来 | 跨时区团队节省人时 |
| **S8** Reviewer agent | claude 写完，codex review；或同事的 agent 来 review | 多 agent 真正分工 |
| **S9** Observer agent | agent 盯 git/CI/metric，重要时主动 ping | 减少 human 主动来查 |
| **S10** ⭐ Artifact-driven Conversation | 人聊出 idea → agent 做 Artifact → 围着改 | 产品形态主轴（新增） |
| **S11** ⭐ Proactive Researcher | agent 盯外部信号，定期主动产 Artifact | "人不能 7×24，agent 可以"（新增） |
| **S12** ⭐ Proactive Initiator | agent 基于观察自己开 topic / 起草 PR | L2 高阶（新增） |

CLI agents 单机做不到 S6 / S9 / S11 / S12 —— 这是 Lets 相对 Cursor / Claude Code / Devin 的真正护城河。

## 4. Wedge 划分（实施优先级）

```
打透（v1.5 / v2 的核心）:
  S2 多人各自 agent       ← 用户和同事的核心日常
  S3 一人多 agent         ← 用户 dogfood 现在的样子
  S6 异步移交（mobile）   ← 区别于 IDE-agent 产品的护城河
  S10 Artifact-driven    ← 产品形态主轴
  L2 Goal Guardian (nudge) ← v1.5 加入

支持但不深做:
  S0 一对一 pair          ← 退回去是 Claude Code CLI，让 CLI 做
  S1 多人围攻一 agent     ← 业界 demand 弱；待用户决定要不要深入
  S7 跨班次移交           ← 靠 typed message `handoff` 实现，不需要专门 UI
  S8 Reviewer agent       ← v2 引入，靠 typed message `review`
  S9 Observer agent       ← v2 引入，靠一个 channel + push 解决

v2 引入:
  S11 Proactive Researcher  ← 长期 interest + 定时扫外部 + 主动产 Artifact
  L1 Observer (内部事件)

v3 引入:
  S12 Proactive Initiator ← agent 自己开 topic / 起草 PR / 等 review

明确"当前不加"（注意措辞，不是"永不"）:
  S4 单 agent async       ← Devin / Manus 的赛道
  S5 autonomous 多 agent  ← AutoGen / CrewAI / Wanman 的赛道
                            未来如果用户场景明确出现需求，可重新评估
```

### 4.1 关于 S5 的修正

之前版本写"永不引入 S5"。**修正：S5 当前先不加，原因是它跟当前 wedge 正交**，而不是产品哲学上排斥。

S5 (autonomous multi-agent) 跟 Lets 的差异：
- Lets：human-in-the-loop / on-the-loop，人始终是 final approver
- S5 路线（Wanman / AutoGen）：agent 自主拍板、自主执行

未来如果：(a) 用户场景明确出现"我希望某些场景下 agent 自己跑完"，并且 (b) Wanman / AutoGen 没占满市场，Lets 可以再评估是否引入。**v1.5 / v2 / v3 都不加**。

### 4.2 关于 S1 的特殊说明

S1（多人围攻一个 agent）业界很少做。原因：**多个人同时引导一个 agent，意图会冲突**。Cursor 都没做 multi-cursor pair。

如果未来想做，形态不能是"两个 human 同时 prompt 一个 agent"，而要是 **"一个 owner human + 多个 suggester human + 一个 agent"**（结对编程 driver / navigator 模型）。

**当前判断**：S1 留作"支持但不深做"。无需专门 UI，靠 topic 内 owner 字段 + 普通 chat message 就能涌现。

## 5. Agent Proactivity Layers（agent 主动性的演进）

| 层 | 含义 | 典型场景 | 时机 |
|----|------|---------|------|
| **L0 Reactive** | 等人派活，干完汇报 | S0 / S3 大部分情况 | ✅ v1.5 |
| **L1 Observer** | 盯内部事件（CI / git / metric），重要时 push | S9 | v2 |
| **L2 Proactive Researcher** | 盯外部环境（论文 / 客户反馈），定期主动产 Artifact | S11 | v2 |
| **L2 Goal Guardian** | 守住对话焦点，偏题时温和 nudge | （新场景，PPT 协作里高频）| **v1.5** |
| **L2 Proactive Initiator** | 基于观察自己开 topic / 起草 PR | S12 | v3 |
| ~~L3 Autonomous~~ | agent 自己拍板自己执行 | S5（Wanman / AutoGen） | **当前不打** |

**人始终是 final approver**。即使 L2 Proactive Researcher 主动产 Artifact，最终采纳与否在人。

## 6. 场景到 UI 载体的映射

| 场景 | 主载体 | UI 关键点 |
|------|--------|----------|
| S0 一对一 pair | DM | 1:1 对话流 |
| S1 多人围攻一 agent | topic + owner 字段 | 多 human + 一 agent，标 owner |
| S2 多人各自 agent | topic + multi @mention | 同 topic，多 agent，区分 owner_human |
| S3 一人多 agent | topic | 一个 topic 里 @claude 和 @codex 分工 |
| S6 异步移交 | mobile **Attention Queue** | 进 app 第一眼看到"有什么事等你" |
| S7 跨班次移交 | typed message `handoff` | "我把这个交给 @X" |
| S8 Reviewer agent | topic + typed message `review` | finding / PR 下的 review thread |
| S9 Observer | channel `#observers` + push | watcher agent 集中 |
| **S10 Artifact-driven** | **每个 topic 自带 Artifact 区** | Context pane Artifact 列表 + 版本切换 |
| **L2 Goal Guardian** | **Task tree + `nudge` message** | 偏题时温和提醒 |
| **S11 Proactive Researcher** | `proactive_finding` message + Attention Queue | agent 主动 push |
| **S12 Proactive Initiator** | 新 topic 出现 + `agent_initiated` 标记 | agent 自己创建的 topic 给 human review |

## 7. 标志场景：PPT 协作（v1.5 第一对外案例）

这是 v1.5 的 **demo**，同时验证以下场景的耦合可行性：

- **S10 Artifact-driven**：PPT 就是 Artifact 本身
- **S2 多人各自 agent**：Neo / Trinity / Morpheus 各带 claude / codex
- **S3 一人多 agent**：Neo 同时驱使 claude 和 codex
- **S6 异步移交**：通勤 Attention Queue 跑通
- **S7 跨班次**：Trinity 周五休假，handoff 给 Neo
- **L2 Goal Guardian**：跑题到团建被 nudge 拉回
- **Agent Spec 协同**：team 改 PPT skill 的 default font

### 7.1 标志剧本（详见 mock）

```
1. Neo 在 #广场 发起：下周研讨会要讲 agent 记忆
2. Trinity + Morpheus 加入；Topic 创建，mode=exploratory
3. Neo @claude 起草 → claude 出 v0（8 页骨架）
4. claude 主动提议 task tree：7 个子任务
5. Trinity 反馈 P4 太薄 → @claude:trinity-air 跨 instance 接手 → v1 (4×6 矩阵)
6. Morpheus 推进 framing：事件 vs 语义
7. Trinity 发现 skill 字号 10pt 太小 → @codex 提议 spec change
8. 团队评审 spec change → adopt → 自动 git commit → 所有 agent reload skill
9. claude 用新 skill 重生成 → v2
10. claude·trinity-air proactive_finding：去年研讨会反馈
11. 三人闲聊扯到周五团建 → claude nudge：建议挪到新 topic
12. claude question：要不要更激进的"何时该忘记"角度
13. Neo decision: adopt v2 with 加文字解释 → v3 final
14. Decision 自动归档到 #decisions
```

### 7.2 这场景为什么是 v1.5 的最佳验证

- **高频** ：白领每月几次 PPT
- **真实多人** ：几乎没有"一个人完整做"的高质量 PPT
- **真实人际激发**：聊主题 / 受众 / 重点是高质量协作
- **真实 Artifact**：PPT 就是 Artifact，不是代码的衍生物
- **真实迭代**：5-10 轮版本是常态
- **真实多类型工作**：写文案 / 找数据 / 做图表 / 调风格 —— 多 agent 真正能分工
- **非工程师友好**：白领日常，不只是程序员
- **价值可量化**：完成时间 / 评审通过率 / 老板满意度

详见 `docs/scenario-pptx.md`（如尚未写则待补）。

## 8. 新章节：目标守护 + 偏题提醒

### 8.1 问题

人类讨论容易歪楼。聊 PPT 聊着聊着扯到团建，扯到一半发现 30 分钟过去了，回不到主线。

### 8.2 设计

**目标分解（Task Tree）** ：每个 topic 在被 agent 识别为"方向已经清楚"后，agent 主动提议初始任务分解。可视化默认是 WBS 风格的树（不是脑图、不是鱼骨图），原因：**WBS 给得出"active task"，脑图不行**。用户可切换到 mind map 形态做发散探索。

**偏题判断**：混合规则
- 连续 ≥ 3 条 message 跟当前 active task 不相关
- AND 时长 ≥ 5 分钟
- AND topic mode = actionable（exploratory 模式宽容度高）
- AND 同一次偏题只提示一次

**`nudge` typed message**：
- 灰底虚线（低调，不刺眼）
- 标签：`温和提醒`
- 三个 quick action：**独立成新 topic**（primary，给偏题内容一个家）/ 回主线 / 略过
- 关键设计原则：**不删聊天、不替人切话题、可关闭**

### 8.3 为什么这是核心差异化

| 产品 | 实时偏题提醒 |
|------|:----------:|
| Slack / Discord | ❌ |
| Linear / Multica | ❌（issue 是 unit，本来就锁主题） |
| Notion AI | ❌ |
| Otter / Krisp | △（事后总结） |
| **Lets** | ✅（实时 + L2 Goal Guardian） |

业界没有产品做实时聚焦。这是 Lets 区别于"被动 chat tool"的关键 signature。

## 9. 单人 vs 多人

**单人能用**，但价值密度低于 2+ 人。设计原则：

- 注册即可用，"邀请同事"是 onboarding 引导而非门槛
- 所有功能（topic / Artifact / Spec / nudge）都不假设 2+ 人
- 单人场景下 Lets 是 **Cursor / Claude Code 的 web 协作面 + Artifact 沉淀面**
- 但**核心 wedge 仍然是 2-8 人小团队**，营销 / 推广话术围绕"团队（哪怕只有一个朋友）"

## 10. 路线图位置

按 `docs/roadmap.md` 的阶段：

| 阶段 | 能跑通的场景 |
|------|------------|
| **v1（已交付）** | 部分 S3：一人多 agent 通过 MCP claim/report |
| **v1.5a Substrate** | 为 S2 / S6 等准备基础设施 |
| **v1.5b Spec Sync** | 真正打通 Agent Spec 协同 |
| **v1.5c PPT demo + Goal Guardian** | **S2 + S3 + S6 + S7 + S10 + L2 Goal Guardian 一次性跑通** |
| v2 | S8 / S9 / S11 / L1 Observer |
| v3 | S12 / 跨设备 / 拓非工程师人群 |
| v4+ | 评估是否引入 S5 (L3 Autonomous) |

## 11. 与其它文档的关系

| 文档 | 与本文关系 |
|------|----------|
| `product-thesis.md` | 给出战略；本文是战略下的场景拆解 |
| `roadmap.md` | 给出时间顺序；本文场景按 roadmap 阶段划分 |
| `agent-spec-collaboration.md` | 解释 Agent Spec 这个核心差异化；本文场景里 PPT 案例引用 |
| `architecture.md` | 给系统分层；本文场景对应 Experience Layer 的功能集合 |
| `core-schema.md` | 定义实体；本文场景的 UI 载体（topic / message / Artifact / task tree）对应这些实体 |
| `branch-model.md` | 定义 branch 语义；本文场景里 spec change 触发 branch 操作 |

如本文跟上述任何文档有冲突，**以本文场景定义为准** —— UI 决策必须从具体场景出发，文档之间需要保持一致时本文是 source of truth。

## 12. Open Questions

1. **S1 要不要深做**：当前判断"不深做"，等用户场景真实出现"多人围攻一 agent"再评估
2. **S9 Observer agent 的实现**：观察什么？什么算"重要"？建议 v2 单独立项设计
3. **L2 Goal Guardian 的频率调优**：5min / 3 条 message 是经验值，需要 dogfood 用户反馈调
4. **跨 organization 协作**：当前所有场景假设同一 org / 同一 GitHub repo。跨 org 是否要支持？v3 之后再考虑
5. **Lets 的"team-shared global spec"**：v3 时再决定要不要做（Path 4），还是项目级 spec 永远是答案
