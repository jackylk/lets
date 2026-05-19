# Lets v1.5 Tracks Overview

> 这是 v1.5 的开发任务分解 + 并行 track + CC vs Codex 分工建议。**不是**单个 implementation plan —— 每个 track 有自己的 plan 文件（`docs/superpowers/plans/2026-05-*-track-*.md`）。

**当前状态**：v1（已交付）→ v1.5（推广同事的目标）尚未开始。

## 1. 五个并行 Track

| Track | 主题 | 包含 | 规模 | 风险 |
|-------|------|------|------|------|
| **A. Schema Substrate** | 数据模型底座 | 三段身份 (humans/agent_roles/agent_instances) · events 表 · messages 表 · 收编现有 4 股流 | 中（12-15 task）| 低（纯 DB / 数据迁移）|
| **B. Network Transport** | 远程接入能力 | HTTP / SSE MCP transport · token-based auth · 容器化 deploy | 中（10-12 task）| 中（涉及 FastMCP 内部）|
| **C. Project Lifecycle** | 项目从无到有 | projects 实体 · project_proposal typed message · GitHub OAuth · 本机 daemon 扩 (git clone / gh repo create) | 大（18-22 task）| 中-高（OAuth flow + 本机 daemon 协调 + GitHub API）|
| **D. Artifact Substrate** | Artifact 抽象层 | Artifact 实体 + version chain + ArtifactSyncAdapter 接口 + GitBackend 实现 | 中（12-15 task）| 低-中（抽象设计 + Git 集成）|
| **E. Onboarding** | 安装 + 首启 | macOS installer (.dmg) · macFUSE + dbay-fuse 打包 · 首启 wizard · Tutorial topic · Lite mode fallback | 大（20-25 task）| 高（installer + system extension + GUI）|

后续 v1.5c 阶段还有 PPT 协作 demo（Google Slides API 集成等），属于 Track D / E 的延伸，**v1.5b 完成后再起 plan**。

## 2. 依赖图

```
        ┌─────────────────────────────────────────────────┐
        │                                                 │
        ▼                                                 │
    Track A                                               │
    Schema Substrate                                      │
        │                                                 │
        ├─────────────┬─────────────┐                     │
        ▼             ▼             ▼                     │
    Track B       Track C       Track D                   │
    Network       Project       Artifact                  │
    Transport     Lifecycle     Substrate                 │
        │             │             │                     │
        └─────────────┴─────────────┘                     │
                      │                                   │
                      ▼                                   │
                  Track E                                 │
                  Onboarding ◀─────────────────────────────┘
                  (集大成)
```

**关键依赖**：
- Track A 是所有其它 track 的前置（schema 不定，后面写啥都是猜）
- Track B / C / D 可在 A 完成后**完全并行**（无相互依赖）
- Track E 依赖 B + C + D 都基本完成（installer 要安装所有这些）

**并行机会**：A 完成后，CC 和 Codex 各拿 2 个 track（一人 B+D，另一人 C），可缩短总时间约 40%。

## 3. CC vs Codex 推荐分工

基于各自特点（**仅作建议，不是硬绑定**）：

| Track | 推荐 | 理由 |
|-------|------|------|
| **A. Schema Substrate** | 任一（先做完）| schema 设计 + 数据迁移，谁先做都行，但**必须 A 完成大家再 fork** |
| **B. Network Transport** | **Codex** | FastMCP transport / token auth / Docker 等工程细节；Codex 擅长系统集成 |
| **C. Project Lifecycle** | **Codex** | GitHub OAuth flow + gh CLI + 本机 daemon 协调 + multi-machine clone；强工程性 |
| **D. Artifact Substrate** | **CC (Claude Code)** | 抽象层设计 + 接口契约 + 跨多个未来 backend 的扩展性；需要"产品 sense"判断哪些不该过度设计 |
| **E. Onboarding** | **CC** | macOS installer / GUI wizard / UX 文案 / 失败回滚的人性化设计 |

如果 CC 和 Codex 同步工作，分工建议：
```
Phase 1 (一起):
  - 任一人写 Track A plan，另一人 review
  - 任一人执行 Track A 实现
  
Phase 2 (并行):
  - CC:    Track D (Artifact) → Track E (Onboarding)
  - Codex: Track B (Network) → Track C (Project Lifecycle)

Phase 3 (会合):
  - 任一人做 integration test（PPT 协作端到端剧本）
```

**反过来也行** —— 如果你的 CC 实例更擅长系统集成（很多 dogfood 跑下来了），可以让 CC 跑 B+C，Codex 跑 D+E。本表只是默认建议。

## 4. 每 Track 的"完成定义"

判断 track 何时算完，便于 hand off 给下一阶段：

### Track A "Done" 标准
- `humans` / `agent_roles` / `agent_instances` / `events` / `messages` 五张表迁移完成
- 现有 work_items.created_by 能正确指向 humans 或 agent_instances
- 现有 status_updates / findings / human_notes 通过 messages 视图查询，结果跟原表一致
- 新 typed messages（chat / status / finding / decision / question / handoff / review / artifact_revision / spec_change / nudge / proactive_finding / task_tree_proposal / system）13 种全部能 insert + query
- API: `POST /api/messages` + `GET /api/topics/{id}/messages` 工作
- pytest 全绿，覆盖率 > 70%

### Track B "Done" 标准
- HTTP MCP transport：另一台机器（或同机不同进程）的 CC 能通过 URL 接入
- Token auth：未带 token 的 MCP 请求 401
- Docker compose 起一个完整 backend
- 同事的 .mcp.json 配置只含 URL，不含本地路径

### Track C "Done" 标准
- 通过 conversation 触发 `project_proposal` → owner approve → 自动调 `gh repo create`
- 多人 approve 后，每个 member 本机 daemon clone 完成
- GitHub OAuth flow 完整（token 落本机 keychain）
- 失败回滚：clone 失败的 member 上 Attention Queue 列表

### Track D "Done" 标准
- Artifact 实体 + version_chain + preview_uri 字段
- ArtifactSyncAdapter 接口 + GitBackend 实现
- 创建 / 读 / 写 / 列版本 / diff 五个核心方法
- 在 mock 真接通：mock 里的 PPT 缩略图能换成 GitBackend 拉出来的 markdown 文件渲染

### Track E "Done" 标准
- macOS .dmg 一键安装：装 AgentBoard.app + dbay-fuse + macFUSE
- 首启 wizard：登录 → 检测 CC/Codex → AgentFS takeover 引导 → 加入 / 创建项目
- Lite mode：跳过 macFUSE，纯 web + git 仍能用
- 5 分钟试金石：第一个朋友从 dmg 双击到加入 topic 发第一条消息 ≤ 5 分钟

## 5. 不在 v1.5a/b 范围（明确推迟）

- Google Slides API 集成 → v1.5c（PPT demo 时再做）
- Goal Card / task tree / nudge 的后端实现 → v1.5c
- 飞书 / 飞书演示 backend → v2
- Object Storage backend → v2
- L2 Proactive Researcher / Memory derivation → v2
- AgentFS Team base → v3

## 6. 推荐执行顺序

```
Week 1-2:  Track A (一起做完，是底座)
              ↓
Week 3-4:  Track B + Track D 并行
              ↓
Week 5-6:  Track C
              ↓
Week 7-8:  Track E + integration test
              ↓
v1.5a/b done, 启动 v1.5c (PPT demo)
```

预估 **6-8 周**完成 v1.5a + v1.5b（不含 PPT demo）。

## 7. Plan 文件清单

每个 track 的具体 implementation plan：

| Track | Plan 文件 | 状态 |
|-------|----------|------|
| A | `2026-05-19-track-a-schema-substrate.md` | ✅ 本轮一起写 |
| B | `2026-05-XX-track-b-network-transport.md` | ⏳ Track A 完成后写 |
| C | `2026-05-XX-track-c-project-lifecycle.md` | ⏳ Track A 完成后写 |
| D | `2026-05-XX-track-d-artifact-substrate.md` | ⏳ Track A 完成后写 |
| E | `2026-06-XX-track-e-onboarding.md` | ⏳ B+C+D 完成后写 |

## 8. Open Questions

1. **Track A 完成后，B/C/D 是否真的能完全并行**？需要在 A 的 schema design 时尽量减少跨 track 的耦合点
2. **CC / Codex 各自怎么 take task**：通过 Lets 黑板（自己 dogfood）？还是约定文件签名机制？建议**用 Lets 自己跑** —— 每个 task 一个 work item，谁 claim 谁做
3. **冲突解决**：如果 CC 和 Codex 都改同一个文件（如 `app/db.py`），怎么协调？建议每个 track 的 schema 改动**只能由一人执行**，其他 track 完成后 rebase
4. **测试基础设施**：当前 Lets 仓库**无任何测试**，Track A 第一个 task 必须建 pytest setup
