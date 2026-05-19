# Product Roadmap

> **Revision 2026-05-19** —— 经过一系列产品讨论，roadmap 经过实质重排：
> - v1.5 拆成 **1.5a Substrate / 1.5b Spec Sync / 1.5c PPT 协作 demo** 三段
> - PPT 协作从 v2 提到 v1.5c（**第一对外推广案例**）
> - 跨设备 / 跨人 / 跨 org 能力按"远程化先于会话"原则重新排序
> - L2 Goal Guardian（守住对话焦点）加入 v1.5c
> - Autonomous 多 agent (L3) 路线措辞改为"当前先不加"，不是"永不"

## 1. Stage 总览

```
v1      Shared State Board (已交付，dogfood 中)
 │
v1.5    Conversation MVP + Spec Sync + PPT 协作（推广同事 / 朋友）
 │      ├── v1.5a Substrate
 │      ├── v1.5b Spec Sync
 │      └── v1.5c PPT 协作 demo + Goal Guardian
 │
v2      拓 Artifact + L2 Proactive (Observer + Researcher)
 │
v3      真团队多设备 + L2 Proactive Initiator + 拓非工程师人群
 │
v4+     可能引入 L3 Autonomous（按当时情况决定）
```

## 2. v1（已交付）

### 已实现
- work_items / agents / status_updates / findings / human_notes
- HTTP API + 本地 stdio MCP
- 一页 web UI（调试面板形态）
- create_work_item / create_feedback / set_work_item_status 三个 MCP 写工具
- 修了两个 v1 真实 bug（DB connection 泄漏 / 嵌套 connection 自锁）

### Success condition（已达成）
- Claude Code 和 Codex 通过本地 MCP 协作完成 dogfood
- 黑板上发布 10 个 T1-T10 工单 + 索引 finding
- 推到 done 的完整生命周期跑通

## 3. v1.5 — Conversation MVP + Spec Sync + PPT 协作

### Goal
让 Lets 成为团队（哪怕只有一个朋友）和他们的 agent 的主协作面，**第一个对外故事是 PPT 协作**。

### v1.5a "Substrate"（基础设施，无可见功能）

不做这一步，后面所有功能都没基础。**这是"推广同事"的硬前置，比 conversation 还重要**。

| 交付 | 目的 | 详细文档 |
|------|------|---------|
| **HTTP / SSE MCP transport** | 同事的 CC / Codex 接入 Lets 后端（替代本地 stdio + venv 路径） | — |
| **三段身份**: `human` / `agent_role` / `agent_instance` | 一个人在两台机器 / 同一 role 多 instance 都不冲突 | — |
| **`events` 表（must-source 集合）** | conversation / coordination 的时序底座；spec change / artifact_revision / nudge 等都落事件 | — |
| **`projects` 实体 + GitHub repo 绑定** + project lifecycle 完整流程 | 一个 Lets project ↔ 一个 GitHub repo，spec change 落地有 git 操作目标 | `project-lifecycle.md` |
| `project_proposal` typed message + 投票 + multi-clone 协议 | 聊出来一个项目 → 多方 approve → owner 创建 GitHub repo → 同事本机 clone | `project-lifecycle.md` §3 |
| **每用户 GitHub OAuth** + token 本机 keychain | clone / push / collaborator 管理 | `project-lifecycle.md` §5 |
| 本机 daemon（基于 dbay-fuse 扩展命令集） | 接 `git clone` / `gh repo create` / `dbay-fuse takeover` 等系统操作 | — |
| **`messages` 表 + 收编现有 4 股流** | status_updates / findings / human_notes / work_items 进度合并成 messages 的 typed variants | — |
| **后端容器化 deploy** + SaaS + self-hosted 双形态 | 单机 dev / VPS / cloud 都跑同一份后端 | `onboarding.md` §11 |
| **token-based auth (最简)** + Lets 自己的 session | 同事接入需要身份 | `onboarding.md` §5.2 |
| **Lets.app + .dmg installer** (mac 优先) | 一键安装，含 macFUSE + dbay-fuse + daemon | `onboarding.md` §4-5 |
| **首次启动 wizard** + Tutorial topic | 5 分钟试金石 | `onboarding.md` §2, §5 |
| **Lite mode**（fallback 无 AgentFS） | 装不了 FUSE 的用户仍能用 80% | `onboarding.md` §6 |
| **Artifact 实体 + `ArtifactSyncAdapter` 抽象层** + `GitBackend` | Artifact 类型分发到不同 backend 的基础设施 | `artifact-sync-strategy.md` §4 |

### v1.5b "Spec Sync"（核心差异化能力）

让 Agent Spec 协同 + 版本化跑通。**这是 Lets 的最强护城河**。

| 交付 | 目的 |
|------|------|
| Lets 后端识别项目 `.claude/skills/` / `CLAUDE.md` / `.mcp.json` 当前状态 | spec change 的事实基础 |
| `spec_change` typed message + diff 预览 + 投票 bar | UI 上的 PR-like 协作 |
| Lets 触发 git commit / revert | 隐藏 git 命令，用户只看到"adopt / revert"按钮 |
| Webhook / 本地 daemon hook：spec change merge 后通知同事 agent reload | 同事 CC 自动同步 spec |
| AgentFS Personal Base 集成（dbay-fuse）| 个人跨设备同步全局 spec / memory |
| Web UI 加 **Project Spec** sidebar 区 + Spec 详情页 | 看到当前 spec 全貌 + 历史 |

### v1.5c "PPT 协作 demo" + Goal Guardian

这是 **v1.5 的对外故事**。

| 交付 | 目的 | 详细文档 |
|------|------|---------|
| **`GoogleSlidesBackend`** 实现（Artifact Sync Adapter 的第二个 backend） | PPT 多人多 agent 并发改不同页面 | `artifact-sync-strategy.md` §5 |
| Google OAuth lazy 弹出（drive.file + presentations scope）| 第一次涉及 PPT 时引导 | `onboarding.md` §7 |
| Server-side PPT 缩略图缓存（getThumbnail PNG）| Web UI 显示 PPT 缩略图 | `artifact-sync-strategy.md` §5.4 |
| Google API rate limiter + outbox（离线时） | 不被限流 / 不阻塞 agent | `artifact-sync-strategy.md` §5.5 |
| `artifact_revision` typed message + inline 缩略图预览 | agent 推出新版本时的 UX | — |
| Context pane 加 **Artifact 区** | 当前 topic 的 Artifact 列表 + 版本切换 | — |
| **Topic mode**: exploratory / actionable + tags 系统 | low-friction creation | `product-thesis.md` §6 |
| **Task tree** 实体（topic 下的目标分解） | Goal Guardian 的基础 | `collaboration-scenarios.md` §8 |
| `task_tree_proposal` typed message（agent 主动提议初始分解） | 不强迫人写 tree | — |
| `nudge` typed message（偏题提醒） | L2 Goal Guardian 落地 | — |
| Context pane 加 **目标分解** 区 | 永久可见 progress + active 任务 | — |
| **Mobile-first Attention Queue**（responsive web）| S6 移动办公 | — |
| 三组 attention 归类：需要决定 / 等你 review / 同事移交 | 早上通勤一眼看到 | — |
| `handoff` typed message | S7 跨班次移交 | — |
| `proactive_finding` typed message | L2 Proactive 第一个 surface（事件型 push） | — |
| 5 分钟试金石 dogfood 测试 | 第一批朋友验证 onboarding 流畅度 | `onboarding.md` §2 |

### v1.5 Success Conditions

1. 团队（2-3 人）用 Lets 协同完成一份**真实交付给老板的 PPT**
2. PPT 制作过程中至少发生 1 次 spec change（改 skill）并被团队 adopt
3. 团队成员在通勤手机上完成至少一次 review + adopt 决策
4. agent 至少触发一次 nudge，用户感觉"恰到好处"
5. **第一个工程师朋友（你之外）愿意把 Lets 作为日常协作工具**

## 4. v2 — Artifact 拓宽 + L2 Proactive 加深

### Goal
让 Artifact 类型超出 PPT，并让 agent 进入"主动研究"模式。

| 交付 | 目的 | 详细文档 |
|------|------|---------|
| **`GoogleDocsBackend` / `GoogleSheetsBackend`** | docx / xlsx 场景 | `artifact-sync-strategy.md` §6.2 |
| **`FeishuBackend`**（大陆备选） | 大陆用户、Google 不可达场景 | `artifact-sync-strategy.md` §5.6 |
| **`ObjectStorageBackend`**（S3/MinIO/R2/OSS） | 图片 / 视频 / 数据集 / 大二进制 | `artifact-sync-strategy.md` §6.3 |
| Artifact 类型扩到 **docx / xlsx / markdown report / data dashboard** | 非 PPT 文档场景 | — |
| 数据分析场景：agent 拉本地数据 / 调内部 API + 出报告 | "agent 真能用本地数据"是关键卖点 | — |
| **L2 Proactive Researcher** | agent 持续监控外部信号（论文 / 新闻 / 客户反馈）+ 主动产 Artifact | `collaboration-scenarios.md` §3 (S11) |
| **L1 Observer** | 内部事件（CI / git / metric）push 到 Attention Queue | `collaboration-scenarios.md` §5 |
| `review` typed message + 二阶 thread | S8 reviewer agent 真做（agent review agent / agent review human） | — |
| Memory 共享层（dbay-fuse memory derivation） | Claude / Codex 看到同一份长期 memory | `agent-spec-collaboration.md` Path 3 |
| `#observers` channel | S9 Observer agent 集中场所 | — |
| Architecture Graph view（仅 R&D 场景）| initiative + hypothesis + 关系 | — |
| Windows full mode（如有需求） | WinFsp 集成 | `onboarding.md` §4.3 |
| Multi-org GitHub repo（个人 vs 组织 account） | 团队有 GitHub Org 时 | `project-lifecycle.md` §8 |

## 5. v3 — 真团队多设备 + 拓人群

### Goal
解决"推广同事"之外的两件事：**多设备 + 跨工种**。

| 交付 | 目的 | 详细文档 |
|------|------|---------|
| Team AgentFS base（dbay-fuse 服务端 + 权限模型） | 跨人共享全局 spec / 长期记忆 | `agent-spec-collaboration.md` Path 4 |
| **`WPSOnlineBackend`** | 中国市场第三选择 | `artifact-sync-strategy.md` §7 |
| 自建 CRDT backend（yjs / automerge） | 高度协作的文本场景 / self-hosted 替代 Google | `artifact-sync-strategy.md` §7 |
| 真多用户多设备：跨机器 + 跨时区 + 离线 / 重连 | 完整团队场景 | `project-lifecycle.md` §4.3 |
| 拓非工程师场景：家庭 / 教研 / 运营 | TAM 扩展 | — |
| **L2 Proactive Initiator** | agent 基于观察自己开 topic / 起草 PR | `collaboration-scenarios.md` §3 (S12) |
| GitHub 深度集成：commits / PRs / CI / 跨 PR 视图 | 工程团队完整 | — |
| MetricRun + MetricResult 摄取 + dashboard | benchmark-driven decision（R&D 场景） | — |
| 用户角色 / 简单权限 | 同事 vs 朋友 vs 客户 | — |
| Multi-tenant 多用户单机（如家庭场景） | 一台电脑两个家庭成员各自账号 | `onboarding.md` §12 |
| Hosted agent runtime（实验） | 非工程师纯 web 用户 | `onboarding.md` §12 |
| 私有 GitHub Enterprise / GitLab / Gitea backend | 企业 self-hosted git | `project-lifecycle.md` §8 |

## 6. v4+ — 长期可能

| 方向 | 触发条件 |
|------|---------|
| **L3 Autonomous 多 agent**（当前不打） | 如果用户场景明确出现"agent 自主拍板"的真实需求，且 Wanman / AutoGen 路线没把市场吃完 |
| 跨 organization 协作 | 用户从单 org 扩到 cross-org 真有需求 |
| Hosted agent runtime（不依赖本地 CC / Codex） | 非工程师非常想用但无法装 CLI |
| Lets Cloud（商业化） | v1.5 开源 / v2 验证 product-market fit 后 |

## 7. 为什么 PPT 协作 + Spec Sync 是 v1.5 第一对外故事

不是简单"换个 demo 场景"，而是 product-market fit 的实质判断：

| 维度 | 代码场景 | PPT 协作场景 |
|------|---------|------------|
| 工程师同事愿意试 | ✅ 高 | ✅ 高 |
| 工程师朋友愿意试 | △ 中 | ✅ 高 |
| 非工程师朋友 | ❌ 零 | ✅ 中 |
| 单次验证时间 | 几天 | 几小时 |
| 价值可量化 | 难 | 易（完成时间 / 评审通过率） |
| 视觉吸引 | 低 | **高（PPT 缩略图直接传播）** |
| 程序员讨厌的事 | — | **PPT 是程序员痛点，工程师也欢迎** |

**Spec Sync 是底层能力，PPT 是它的 demo**。两者一起出，才能让"Lets 改一个 skill，所有人 PPT 风格一致"的故事说圆。

## 8. 为什么 v1.5 不能跳过 Substrate（1.5a）直接做 Conversation

不动 substrate 就做 conversation，会撞 3 个真坑：

1. **没有 HTTP MCP，同事接不上后端** —— PPT 场景需要 ling / Morpheus 的 CC 也能写 stream message
2. **没有三段身份，@mention 解析不出来** —— `@claude` 该 ping 哪个 claude？
3. **没有 events / messages 表统一，conversation 跟 status_updates / findings 时序混乱** —— UI 看到的"agent 09:31 发了 finding"和 activity feed 顺序对不上

这三件事不解决，conversation 看起来跑通了但**用起来一定有 bug**。所以 1.5a 必做、必先做。

## 9. Dogfood Questions per Stage

### v1.5 阶段
- 团队是不是真的能用 Lets 协同写出一份可交付 PPT
- 朋友进来 30 分钟内能不能搞清楚怎么用
- spec change 流程会不会被嫌烦
- nudge 提醒触发时用户感觉是恰到好处还是讨厌
- mobile 上做 review 是不是真比电脑前更方便

### v2 阶段
- L2 Proactive Researcher 产的 Artifact 命中率（用户 adopt 比例）
- memory 跨 agent 共享是不是真减少了重复劳动
- 数据分析 / docx / xlsx 场景能不能立得住

### v3 阶段
- 非工程师朋友能不能不依赖工程师朋友独立用
- 跨设备同步在真团队下稳定吗
- 商业化路径选择：开源 + Cloud？纯 SaaS？纯开源？

## 10. Strategic Sequence

```
你（dogfood）            ling（你工程师同事）         非工程师朋友
   │                          │                            │
   v1                          │                            │
   │                          │                            │
   v1.5a Substrate ──────────► （ling 接入）                │
   v1.5b Spec Sync                                          │
   v1.5c PPT demo ────────────────────────────────────────► （朋友试用 PPT 场景）
                                                            │
                                                            v2 拓 Artifact
                                                            v3 拓非工程师
```

每个阶段的"扩用户"动作严格挂在前置能力完成之后。**不让 conversation MVP 在 substrate 没好之前外推**，避免推广出去之后 fold back。
