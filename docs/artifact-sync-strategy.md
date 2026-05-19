# Artifact Sync Strategy

## 1. 这份文档解决什么

**Artifact 同步**的形态跟 Artifact 类型强相关。代码走 Git 完美；PPT 走 Git 灾难（二进制 zip 无法 line-merge、多 agent 改不同页面冲突）。本文给 Lets 一个统一的"按类型分发到合适 backend"的策略。

本文与：
- `agent-spec-collaboration.md` —— spec 走 Git / AgentFS，不在本文范畴
- `project-lifecycle.md` —— project 框架走 Git，本文管 project 内部 Artifact

## 2. 三个系统的分工（明确边界）

Lets 内部并存三类同步系统，**职责不重叠**：

| 系统 | 负责 | 不负责 |
|------|------|--------|
| **AgentFS** (dbay-fuse) | Agent Spec / Memory / Session history / 跨设备同步**个人**配置 | ❌ Artifact 同步、❌ 团队共享 spec |
| **Git** | 代码 / Markdown / 项目级 Spec / 配置文件 | ❌ PPT/Doc/Sheet 实时多人编辑、❌ 大二进制 |
| **Artifact Sync Adapter** | 按类型分发到具体 backend：Git / Google Workspace / 飞书 / Object Storage / CRDT | ❌ spec 协同 |

**只用 Git 不行 / 只用 AgentFS 不行 / 必须有第三层**。这是产品的真实要求，不是凑数。

## 3. 按 Artifact 类型分对照表

| 类型 | 协作粒度 | Git 行不行 | 推荐 backend (v1.5) | v2/v3 备选 |
|------|---------|:----------:|---------------------|----------|
| 源代码 / config | commit 级，并行改不同文件 | ✅ 完美 | **Git** | — |
| Markdown 文档 | 行级 | ✅ | **Git** | — |
| **PPT** (.pptx) | **逐页**，A 改 P1 同时 B 改 P2 | ❌ 二进制 zip+XML | **Google Slides API** | 飞书演示 / WPS Online |
| Doc (.docx) | 段落 / 标题 | ❌ | **Google Docs API** | 飞书文档 |
| Spreadsheet (.xlsx) | 单元格 | ❌ 行合并难 | **Google Sheets API** | 飞书表格 |
| 数据集（小，<10MB）| 块级 | △ csv 可，二进制不行 | Git LFS | Object Storage |
| 数据集（大）| 不分段 | ❌ | **Object Storage** (S3-compatible) | — |
| 图片 / 截图 / 视频 | 不分段 | ❌ 大二进制 | **Object Storage** | CDN |
| Web 原型 / Demo 站 | commit 级 | ✅ | **Git + Vercel/CF preview** | — |
| 分析报告（含图表 + 数据 + markdown） | 复合 | △ markdown 走 git，图表外挂 | Git + Object Storage | — |
| Memory / Annotations | 高频小写 | ❌ commit 风暴 | **AgentFS** (dbay-fuse) | — |
| Agent Spec | 团队共享 | ✅ | **Git** | — |

## 4. Artifact Sync Adapter 抽象

Lets 后端引入抽象层 `ArtifactSyncAdapter`。Agent 不需要知道用什么 backend：

### 4.1 统一 API

```
# Agent 视角的统一接口
update_artifact(
  artifact_id="ai-memory-talk.pptx",
  patch={page: 4, operation: "replace_layout", layout: "matrix-4x6"},
  reason="改成 4x6 矩阵 per Trinity",
  agent_name="claude:trinity-air"
)
→ returns new_version, sync_status

read_artifact(artifact_id, version=null)
→ returns content + preview_urls + metadata

list_versions(artifact_id)
→ returns version_history

diff_versions(artifact_id, v1, v2)
→ returns diff (backend-specific 格式)
```

### 4.2 后端 dispatch

```
Artifact Sync Adapter
├── GitBackend
│   ├── update_artifact: write file, git add, git commit, git push
│   ├── read_artifact:   git show
│   └── versions:        git log
│
├── GoogleSlidesBackend
│   ├── update_artifact: presentations.batchUpdate API
│   ├── read_artifact:   presentations.get + pages.getThumbnail
│   └── versions:        revisions.list (Google Drive API)
│
├── GoogleDocsBackend / GoogleSheetsBackend
│   └── (类似)
│
├── FeishuBackend
│   └── (类似，国内备选)
│
├── ObjectStorageBackend
│   ├── update_artifact: PUT object (with content-hash)
│   └── versions:        S3 versioning / 自建 version chain
│
└── AgentFSBackend
    └── (memory / session 类，前面 spec collab 文档讨论过)
```

### 4.3 dispatch 规则

每个 Artifact 创建时确定 backend（不强制锁定但**默认根据类型推荐**）：

| Artifact type 字段 | 默认 backend |
|-------------------|-------------|
| `pptx` | `google-slides` |
| `docx` | `google-docs` |
| `xlsx` | `google-sheets` |
| `markdown` / `code` / `config` | `git` |
| `image` / `video` / `binary` | `object-storage` |
| `memory_note` / `annotation` | `agentfs` |
| `web` / `prototype` | `git` |

用户在创建时可改 backend（high-power user）。

## 5. Google Slides API 集成（v1.5 PPT 场景必做）

PPT 是 v1.5 标志场景，下面是具体集成方式。

### 5.1 关键 API 能力

| 需求 | API |
|------|-----|
| 创建新 deck | `presentations.create` |
| 改某页 layout | `presentations.batchUpdate` (createSlide / deleteObject / applyLayout) |
| 改 textbox 文字 | `updateTextStyle / replaceAllText` |
| 加图表 | `createSheetsChart` |
| 拿每页缩略图 | `presentations.pages.getThumbnail(thumbnailMimeType=PNG, size=800x450)` |
| 拿全 deck 元数据 | `presentations.get` |
| 监听变更（webhook） | Google Drive API `files.watch` |
| 版本历史 | Drive API `revisions.list` |

### 5.2 多 agent 并发安全

Google Slides 后台用 OT（operational transform）保证多 client 并发不冲突。Agent A 改 P1 同时 Agent B 改 P4 **不需要 Lets 自建锁**。

但需要：
- Lets 后端做 **rate limiting**（每 agent < 60 ops/min），避免被 Google 限流
- **批 batch update**（agent 一次改多处时合并成一个 batchUpdate 请求）
- 失败 retry：Google API 偶发 5xx，retry with backoff

### 5.3 Token 管理

每个 member 第一次创建/读取 PPT-type Artifact 时弹 OAuth：

```
[Onboarding moment]
为了让 agent 直接改 Google Slides，需要授权访问 Google Drive。
Scopes:
- drive.file        (仅你 / 你的 agent 创建的文件)
- presentations     (读写 Slides)
不会读取你的其它 Drive 文件。

[Authorize]  [Skip - 我不做 PPT]
```

Token 存本机 keychain（同 GitHub token）。Lets 后端不存 user OAuth token。

### 5.4 PPT 在 Lets 里长什么样

Artifact 实体在 Adapter 抽象下：

```
{
  id: art_xxx,
  type: "pptx",
  backend: "google-slides",
  
  # Google-specific
  google_presentation_id: "1AbcDef...",
  google_drive_file_id: "...",
  
  # Cache (Lets 自己维护)
  preview_urls: [
    "/api/artifacts/art_xxx/page/1/thumb.png",  ← Server cache 自己的预览
    ...
  ],
  version_chain: [
    { version: "v0", revision_id: "rev_abc", created_at: ..., created_by: claude_neo_mbp },
    { version: "v1", revision_id: "rev_def", created_at: ..., created_by: claude_trinity_air },
    ...
  ],
  
  # 跟 topic 的关系
  topic_id: t_xxx,
  current_version: "v3",
  spec_used: [".claude/skills/research-talk-style v3"],  # 用了哪些 spec 生成的
}
```

Agent 改 PPT 的 message：

```
claude·trinity-air [artifact_revision v1]
  ◇ ai-memory-talk.pptx · v1
  改动：P4 改成 4×6 矩阵（4 个产品 × 6 个维度）
  
  [缩略图序列：8 张 PNG，P4 高亮]
  [open in Google Slides]  [diff with v0]
```

### 5.5 离线 / Google 不可达

- Cache 缩略图在 Lets 后端，断网时仍可看
- 操作进入 outbox，恢复后批量回放（类似 dbay-fuse outbox 模型）
- Lets UI 顶部条提示 "Google Slides 不可达，change 暂存"

### 5.6 大陆用户 fallback：飞书演示 API

Google 在大陆不可达。提供 **飞书（Lark）演示文档 API** 作为同等 backend：

| Google | 飞书 |
|--------|------|
| presentations.batchUpdate | docx_v1.documents.blocks.batch_update |
| presentations.get | docx_v1.documents.get |
| pages.getThumbnail | 飞书 SDK 缩略图 |
| OAuth | 飞书 OAuth |

用户在创建 PPT Artifact 时可选 backend：`google-slides` / `feishu-deck`。Project 级别可设默认。

WPS Online 作为第三选择（v2 评估）。

## 6. 各 backend 详细对照

### 6.1 GitBackend

| 项 | 说明 |
|----|------|
| 操作 | filesystem write + git add + commit + push |
| 版本 | commit hash 是 version |
| diff | git diff |
| 多 agent 并发 | merge / rebase（agent 默认 --rebase before push） |
| 离线 | local commit, push deferred |
| OAuth | GitHub OAuth（已在 §project-lifecycle） |
| 用途 | 代码 / Markdown / 项目级 Spec |

### 6.2 GoogleSlidesBackend / GoogleDocsBackend / GoogleSheetsBackend

| 项 | 说明 |
|----|------|
| 操作 | API batchUpdate |
| 版本 | Drive API revisions（自动）+ Lets 自己的 version chain（语义级） |
| diff | Backend-specific（缩略图对比 / 段落 diff） |
| 多 agent 并发 | Google OT 内建 |
| 离线 | outbox → 恢复后回放 |
| OAuth | Google OAuth, scopes `drive.file` + product-specific |
| 用途 | PPT / Doc / Sheet 实时多人协作 |

### 6.3 ObjectStorageBackend

| 项 | 说明 |
|----|------|
| 操作 | PUT object，内容哈希作为 key |
| 版本 | 多版本对象 / 自建 version chain |
| diff | 无 line-diff，提供 metadata diff |
| 多 agent 并发 | 不支持原地编辑，只支持替换 |
| 离线 | upload deferred |
| 用途 | 图片 / 视频 / 大二进制 / 数据集 |
| Backend 选择 | self-hosted MinIO / S3 / R2 / OSS（用户在 deploy 时配） |

### 6.4 AgentFSBackend

| 项 | 说明 |
|----|------|
| 操作 | POSIX 文件 op via FUSE |
| 版本 | DBay 服务端 PG version chain |
| diff | 文件级 |
| 多 agent 并发 | personal base 是单用户多 agent；team base 待 v3 |
| 用途 | Memory / Session / 个人配置 |

详见 `agent-spec-collaboration.md`。

## 7. v1.5 实施清单

### v1.5b 落地

| 工作 | 描述 |
|------|------|
| `ArtifactSyncAdapter` 接口定义 | Python / TS interface |
| `GitBackend` 实现 | 代码 / markdown 场景跑通 |
| Artifact 实体加 `type` / `backend` / `version_chain` / `preview_urls` 字段 | DB schema |
| Web UI 显示 Artifact 区 + 版本切换 | 已在 mock 验证形态 |

### v1.5c 落地（PPT 场景必需）

| 工作 | 描述 |
|------|------|
| `GoogleSlidesBackend` 实现 | API 集成 + OAuth flow |
| Server-side thumbnail cache | png 缓存到 Lets 后端 |
| `artifact_revision` typed message + inline thumbnail | Stream UI |
| Rate limiter | Google API 配额保护 |
| 离线 outbox | 网络断时不阻塞 agent |

### v2 落地

| 工作 | 描述 |
|------|------|
| `GoogleDocsBackend` / `GoogleSheetsBackend` | docx / xlsx 场景 |
| `ObjectStorageBackend` | 图片 / 视频 / 数据集 |
| `FeishuBackend` | 大陆用户 fallback |
| Artifact 类型间转换（如 docx → markdown）| 跨 backend 数据迁移 |

### v3 落地

| 工作 | 描述 |
|------|------|
| `WPSOnlineBackend` | 中国市场第三选择 |
| 自建 CRDT backend（yjs / automerge）| 高度协作的文本场景（如长 doc 实时打字）|
| Team AgentFS base | 跨人共享全局 memory |

## 8. 风险与决策原则

### 8.1 Vendor lock-in

依赖 Google API 是一种 vendor lock。Mitigation：
- **Adapter 抽象**让 PPT 内容可以"导出 + 切 backend"（v2 加）
- 大陆备选（飞书）从一开始就在 roadmap
- 用户 own 自己的 Google Drive 文件，不是 Lets 持有

### 8.2 隐私 / 数据出境

敏感场景（如医疗 / 金融 / 国企）不能用 Google：
- v1.5 接受这个限制（PPT 推广目标用户是开发者 + 朋友，敏感场景非首选）
- v2 加飞书私有化 / WPS 等国内方案
- v3 评估自建 CRDT，完全 self-hosted

### 8.3 多 backend 状态一致性

如果一个 topic 同时有 PPT (Google) + 数据集 (S3) + 代码 (Git) + 笔记 (AgentFS)：
- 不强制原子一致性
- 每个 Artifact 独立同步
- Lets 后端汇总 view 显示各 Artifact 当前状态
- "Project version" 是逻辑标签，用户可以在某时刻标 "v3 final"，记录此时各 backend 的 version snapshot（不强制可恢复，提供 traceability）

### 8.4 性能 / 延迟

Google API 比 Git 慢（一次 PPT 编辑 = 一次 HTTP RTT）：
- Lets 用户的"看到"延迟主要取决于 thumbnail cache 刷新时间
- 后端用 long-polling + cache invalidation 把"agent 改完了 → 我屏幕上看到新缩略图"压到 < 3 秒
- 缩略图 lazy load

## 9. 测试场景

### v1.5c PPT 协作 demo 必须验证

1. **Neo / Trinity / Morpheus 三方 + 各自 agent，并发改不同页面** —— 不冲突
2. **Trinity 离线 → 改了 P5 → 上线** —— 改动正确同步
3. **Google API 5xx** —— retry 自动 / 用户感觉不到
4. **OAuth 过期** —— 友好提示，不删 Artifact
5. **缩略图 < 3 秒同步**
6. **从 v0 一路改到 v5 final，版本链完整可回退**

### v1.5 普适 Artifact 验证

1. **代码场景**：Git backend 完整 commit-push-pull cycle
2. **混合 Artifact**：同一 topic 有 PPT + 代码 + 数据集，状态独立可见
3. **跨 backend 引用**：PPT 的 P3 引用了某 csv 数据，csv 改了 PPT 显示"data updated"提示

## 10. Open Questions

1. **PPT 内的图表是否绑定到 sheet**：v2 评估（Google Slides 支持 linked chart）
2. **Lets 自己要不要存 PPT 本地拷贝**：v1.5 不存，依赖 Google Drive；v2 评估"导出为 .pptx 落本地"
3. **Artifact 跨 project 复用**：当前每个 Artifact 属于一个 project，跨 project 引用怎么做（如"复用上次的 PPT 模板"）—— v2
4. **Real-time editing UI（看到 ling 的鼠标光标在 P3）**：v3 才考虑（Google Slides 本身有这能力，Lets 是否要 mirror 到 web UI 待评估）
5. **CRDT 自建路线**：v3 真做的话用 yjs / automerge？提供 self-hosted PPT 替代？
