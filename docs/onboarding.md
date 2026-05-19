# Onboarding

## 1. 这份文档解决什么

让朋友/同事**从点击 installer 到加入第一个 topic 发出第一条消息 ≤ 5 分钟**。

这是 Lets v1.5 推广的硬指标。做不到，所有 v1.5 能力（spec sync / PPT 协作 / Goal Guardian）都白搭。

## 2. 5 分钟试金石

```
00:00  点击安装链接 / 收到邀请邮件
00:30  下载完成（installer < 30MB）
01:00  允许 macFUSE system extension（重启可选 - 见 §5.2）
01:30  Installer 完成 → 自动打开 Lets 浏览器 dashboard
02:00  GitHub OAuth 登录（一次性）
02:30  检测到 Claude Code 已安装 → 一键 AgentFS takeover
03:00  接受邀请 → 自动 clone 项目到 ~/work/lets-projects/
04:00  进入项目 topic
05:00  发出第一条消息：「在了」
```

**任何一步超时（如等 macFUSE 授权 > 90s）必须有友好的等待界面**，不能让用户对着"无响应"屏幕。

## 3. 用户分类与差异化路径

| 用户 | 已有 | 路径 |
|------|------|------|
| **工程师同事**（你 dogfood 主对象） | CC / 命令行 / GitHub 账号 | Full mode，5 分钟跑通 |
| **工程师朋友**（你推广目标） | CC 或可装 / GitHub 账号 | Full mode，需要装 CC 时多 5 分钟 |
| **非工程师朋友**（PPT 场景） | 大概率没装 CC，没 GitHub 习惯 | **见 §6 Lite mode** |
| **企业 / 公司笔记本被管控** | 装不了 FUSE | **Lite mode** |
| **Windows 用户** | FUSE 用 WinFsp 复杂 | **Lite mode**（v1.5 不打 Windows full mode） |

## 4. Installer 流程（Full Mode）

### 4.1 macOS（v1.5 主目标平台）

下载 `Lets.dmg` (~30 MB)。

打开后用户看到 4 步引导：

```
[Step 1/4] 欢迎 ────────────────────────────────────
  Lets 是和团队一起聊一聊、让 agent 把想法做出来的协作工作台。
  
  本安装需要 ~3 分钟，安装内容：
  ✓ Lets.app          → /Applications
  ✓ lets-daemon       → 后台运行，启用跨设备同步
  ✓ macFUSE                 → 让你和同事的 agent 共享配置（可选）
  ✓ dbay-fuse               → AgentFS 客户端
  
  [Install]   [Custom...]   [Cancel]

[Step 2/4] 系统授权 ────────────────────────────────
  安装 macFUSE 需要你在「系统设置 → 隐私与安全」里授权一次。
  
  这是 macOS 的安全机制，只需操作一次。如果你看到红色阻止提示，
  按这里的图示点击「允许」。
  
  [打开系统设置]   [跳过 - 用 Lite mode]
  
[Step 3/4] 重启（条件） ─────────────────────────────
  macFUSE 首次安装需要重启系统。
  你的浏览器 / 文档会被保存。
  
  [Restart Now]   [Restart Later]
  
  ↑ 如果用户系统已经有 macFUSE，跳过本步

[Step 4/4] 启动 Lets ───────────────────────
  ✓ 安装完成
  
  下一步：登录 / 加入项目
  
  [Launch Lets]
```

### 4.2 Linux

`.deb` / `.rpm` 包，apt/dnf 安装。fuse3 通常预装。无需重启。

### 4.3 Windows（v1.5 不主推）

WinFsp 比 macFUSE 复杂，文档说明走 **WSL2 + Linux 路径**，或 **Lite mode**。

## 5. First-Run Flow

### 5.1 启动 Lets.app

自动打开默认浏览器 `http://localhost:7000` 或托管版 `https://lets.dev`。

托管版优势：朋友通过邀请链接进来时，无需自己装 server，只装 client/daemon。

### 5.2 登录

```
[Welcome to Lets]
  
  [Sign in with GitHub]    ← 推荐
  [Sign in with Email]
  [Use Self-hosted instance]
  
  没有账号？点 GitHub 自动注册。
```

GitHub OAuth 默认收 `read:user` + `repo` 两个 scope。后者用于创建/clone 项目（详见 `project-lifecycle.md`）。

### 5.3 检测本机环境

后台 daemon 已经启动，扫描：

| 检测 | 行为 |
|------|------|
| Claude Code 已安装？ | ✅ 显示版本号 + "下一步：连接到 Lets" |
| Codex CLI 已安装？ | ✅ 同上 |
| 都没装？ | 引导安装：[安装 Claude Code（推荐）] [手动配置 ▼] |
| macFUSE 安装？ | 如装好 → AgentFS 可用；如未装 → 提示 Lite mode 路径 |
| GitHub OAuth 完成？ | 自动获取 |
| Google OAuth？ | **不一上来就问**，第一次需要时再问（lazy） |

### 5.4 AgentFS Takeover 引导（Full mode）

```
[一次性配置]
  
  Lets 想接管以下目录，让你的配置可以跨设备同步、
  让同事的 agent 知道你的项目背景：
  
  ✓ ~/.claude/CLAUDE.md          → 同步到 personal base
  ✓ ~/.claude/memory/            → 同步到 personal base  
  ✓ ~/.claude/projects/          → 同步到 personal base
  
  - 你的代码 / 文件**不会**被同步
  - 你随时可以 [Disable AgentFS] 回到原状（自动恢复 backup）
  
  [Enable - 推荐]   [Skip - 用 Lite mode]
  
  ▼ 详细说明（隐藏）
  AgentFS 由 dbay-fuse 提供，配合 DBay 服务做跨设备 / 跨 agent 状态同步。
  Backup 在 ~/.dbay/backups/，禁用时一键恢复。
```

启用后：
- daemon 后台 `dbay-fuse mount` + `takeover`
- 显示同步状态："3 文件 in sync · last sync 5s ago"

### 5.5 加入或创建第一个项目

```
[你看起来是第一次来 Lets]
  
  [✦ 创建新项目]
  [📨 我有邀请链接 ↓]
  
  ▼ 已知项目（如你被邀请过）
  ├── echomem-demo (邀请人: Neo)  [Approve & Join]
  └── ...
```

接受邀请 → 自动走 §`project-lifecycle.md` §4.1 加入流程 → 本机 clone 完成。

### 5.6 Tutorial Topic（自动生成）

首次加入项目后，Lets 自动在项目里创建一个 `#tutorial` topic：

```
[topic: tutorial · 你的 agent 跟你打个招呼]

lets-bot · 09:00
  欢迎 @Trinity。这是个 demo topic，跟你的 Claude Code 试试。
  
  在 composer 里输入：
    @claude  今天天气如何
  按 ⏎ 发送。
  
  你的 Claude Code 会通过 Lets 看到这条 message，
  在你本机跑一次，把回复发回这里。
  
  [试试]
```

完成第一次发送后，bot 给 high-five："🎉 你的本机 agent 跟 Lets 跑通了"。

之后引导用户进 #广场 / 其他 topic。

## 6. Lite Mode（无 AgentFS Fallback）

**为谁**：
- 装不了 FUSE（公司管控 / Windows / 旧 Linux 内核）
- 非工程师朋友，对 system extension 授权害怕
- 临时试用 / 不想装 daemon

**功能差异**：

| 功能 | Full Mode | Lite Mode |
|------|:--------:|:--------:|
| Topic / Conversation | ✅ | ✅ |
| Artifact 协作（PPT 走 Google API） | ✅ | ✅ |
| Project Spec 协同（Git） | ✅ | ✅ |
| 跨设备同步个人配置 | ✅ | ❌ |
| 跨 agent 共享 memory | ✅（v2） | ❌ |
| 全局 ~/.claude/ 同步 | ✅ | ❌（每设备各自管） |
| Agent Spec 协同 + 版本化 | ✅ | ✅（项目级 spec 走 git，全局个人不同步） |
| Goal Guardian / nudge | ✅ | ✅ |
| Attention Queue | ✅ | ✅ |

**关键洞察**：Lite mode 覆盖 80% v1.5 功能。PPT 协作场景完全 OK（Artifact 通过 Google API 同步，跟 AgentFS 无关）。

**升级路径**：用户在 Lite mode 用了一阵想升级，settings 里有「Enable AgentFS」按钮 → 走一次 §5.4。

## 7. OAuth Token 收集时机

**不要一上来全问**。按需 lazy：

| 时机 | 问什么 | 为什么这时问 |
|------|--------|-------------|
| 登录 | GitHub OAuth (`read:user`) | 身份必需 |
| 第一次创建项目 / 加入项目 | GitHub OAuth (`repo`) | 需要 clone / push |
| 第一次涉及 PPT-type Artifact | Google OAuth (`drive.file` + `presentations`) | PPT 协作必需 |
| 第一次涉及 Docs / Sheets | Google OAuth (各自 scope) | 同上 |
| 大陆 fallback：选飞书时 | 飞书 OAuth | 第一次需要时 |

每次 OAuth 都有：
- 一段人话解释为什么
- "你可以稍后再来这里授权"的 escape
- Token **不上传到 Lets 后端**，留本机 keychain

## 8. Failure Recovery

每个步骤的失败都要有 graceful path：

| 步骤 | 失败可能 | Recovery |
|------|---------|---------|
| Download installer | 网络断 | 提示，可换镜像 / 用户重试 |
| macFUSE 装 | system extension 被阻止 / 旧版本冲突 | 提供 [跳过 - Lite mode] + 详细说明链接 |
| 重启 | 用户拒绝立即重启 | OK，下次启动 daemon 时检查并提示 |
| GitHub OAuth | 用户取消 / token 失败 | 留在登录页，可重试 |
| CC 检测 | 没装 | 引导安装链接（不阻塞 onboarding，可先进 read-only 模式） |
| AgentFS takeover | dbay-fuse mount 失败 | 详细错误 + [Try Again] + [Fall back to Lite] |
| 项目 clone | 路径冲突 / 网络断 | 提供选别的路径 / 重试 |
| Tutorial topic 失败 | 用户的 CC 没正确接入 | 显示 troubleshoot + 联系入口 |

## 9. 默认值 / 最小操作

降低决策疲劳：

| 选项 | 默认 |
|------|------|
| Local path for project | `~/work/lets-projects/<slug>` |
| AgentFS takeover | 启用（用户可关） |
| 自启动 daemon | 启用 |
| Theme | follow system |
| Language | 自动检测 |
| 通知 | 重要 push 启用，闲聊静音 |
| Mobile push | 默认不开（需 enable） |

## 10. 实施清单

### v1.5a 末段

| 工作 | 描述 |
|------|------|
| Lets.app + .dmg installer | 包装 dbay-fuse + daemon + macFUSE pkg |
| 首次启动 wizard UI | 上面 §4.1 / §5.x 步骤 |
| Daemon 检测本机环境 | CC / Codex / fuse / OAuth status |
| Lite mode 切换 | settings page |
| Tutorial topic 自动生成 | 加入项目后第一个 topic |
| GitHub OAuth 流程 | 一次完成 |
| Token keychain 存储 | macOS keychain / Linux libsecret |

### v1.5c

| 工作 | 描述 |
|------|------|
| Google OAuth lazy 弹出 | 第一次涉及 PPT 时 |
| Onboarding 失败统计 | 看哪一步流失率最高 |
| 5 分钟试金石 dogfood | 第一批朋友测试 |

### v2

| 工作 | 描述 |
|------|------|
| Windows full mode（如有需求） | WinFsp 集成 |
| 飞书 OAuth | 大陆用户 |
| Hosted agent 模式（实验） | 非工程师纯 web 用户 |

## 11. 衡量指标

每个 onboarding 阶段记录指标，dogfood 期间持续优化：

| 指标 | 目标 |
|------|------|
| Installer download → click rate | > 70% |
| Install 完成率 | > 85% (mac) |
| FUSE 授权完成率 | > 75% |
| 首次启动到 Tutorial 完成 | < 5 分钟（中位数）|
| 7 日留存（注册后第 7 日还活跃） | > 40%（第一批朋友） |
| Lite mode 占比 | < 30%（说明 Full mode 够顺） |

## 12. Open Questions

1. **Lets 是 SaaS 托管 + 本地 daemon 模型，还是纯 self-hosted**：v1.5 提供 hosted 版（lets.dev）+ self-hosted Docker；用户在登录时选 instance
2. **托管版的数据隐私**：用户 prompt / message / artifact metadata 存哪？建议默认存 Lets SaaS Postgres，企业版可 self-host
3. **离线 onboarding**（首次启动无网络）：v1.5 不支持完全离线 onboarding；要求至少一次联网完成首次 OAuth + project sync
4. **多用户同一台机器**（家庭电脑两个家庭成员用）：v3 评估；当前一台机器一个 Lets 账号
5. **Trial mode / 看官网就能体验**：v1.5 提供"无需安装的 demo project"作为 marketing entry，但**真实使用必须安装**（本地 agent 必需）
6. **uninstall 流程**：必须有干净的 uninstall（恢复 ~/.claude/ backup + 删 daemon + 删配置）
