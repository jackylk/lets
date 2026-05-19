# Lets Layer Model

## 1. Overview

```text
┌─────────────────────────────────────────────────────────────┐
│ Conversation Layer                                          │
│ 人和 agent 在哪里说话                                       │
├─────────────────────────────────────────────────────────────┤
│ Coordination Layer                                          │
│ 谁在做什么，怎么避免撞车                                   │
├─────────────────────────────────────────────────────────────┤
│ Research Layer                                              │
│ 我们在探索什么，当前相信什么                               │
├─────────────────────────────────────────────────────────────┤
│ Evidence Layer                                              │
│ 我们凭什么这么判断                                         │
├─────────────────────────────────────────────────────────────┤
│ Shared State Layer                                          │
│ 这些状态怎样跨人、跨 agent、跨设备保持一致                 │
└─────────────────────────────────────────────────────────────┘
```

## 2. Conversation Layer

### 回答的问题

- 我在哪里和 Claude Code、Codex 对话？
- 我能不能在一个界面里 @ 多个 agent？
- agent 的回复能不能回到同一个 thread？

### 核心对象

- channel
- DM
- thread
- message
- mention

### 界面形态

- 左侧频道和 agent 列表
- 中间消息流
- 支持 `@claude`、`@codex`

### 一句话

```text
Conversation Layer = 人和 agent 的共同入口
```

## 3. Coordination Layer

### 回答的问题

- 谁在做什么？
- 哪个任务已经被 claim？
- 哪个 agent 卡住了？
- 后来的 agent 应该接什么，避免重复？

### 核心对象

- work item
- claim
- handoff
- presence
- status

### 界面形态

- workboard
- agent 状态
- blocker
- recent activity

### 一句话

```text
Coordination Layer = 当前怎么协同
```

## 4. Research Layer

### 回答的问题

- 我们在探索哪几条路线？
- 每条路线在验证什么假设？
- 哪些想法只是 idea，哪些已经升成 initiative？
- 哪些 finding 改变了当前判断？
- 哪些路线已经被否决？

### 核心对象

- idea
- initiative
- hypothesis
- finding
- decision
- architecture relation

### 界面形态

- architecture graph
- idea inbox
- initiative detail
- decision history

### 一句话

```text
Research Layer = 我们怎么想
```

## 5. Evidence Layer

### 回答的问题

- 我们凭什么相信这条路线更好？
- 哪个 commit 带来了哪个结果？
- benchmark 和 baseline 是否可比？
- 哪个 PR 支撑了哪个 finding？

### 核心对象

- code branch
- commit
- pull request
- metric run
- metric result
- artifact
- benchmark report

### 界面形态

- metrics dashboard
- branch / commit links
- experiment history
- comparison tables

### 一句话

```text
Evidence Layer = 我们凭什么这么想
```

## 6. Shared State Layer

### 回答的问题

- 为什么 Claude Code 和 Codex 都能看到同一份状态？
- 为什么多个设备上还能同步？
- 为什么一个 agent 领了任务，另一个 agent 立刻知道？
- 为什么探索中的结论不会直接污染全局事实？

### 核心对象

- typed state objects
- branch-aware state
- presence state
- promotion
- event history
- concurrent updates

### 界面形态

- 一般不直接暴露成页面
- 但所有页面都依赖它

### 一句话

```text
Shared State Layer = 让前四层真正成为一个系统的底座
```

## 7. Concrete Example: echomem

### Conversation

```text
你在 #track-b 里说：
“先别继续 always-on inject，优先研究 topic-indexed WM。”
```

### Coordination

```text
Claude Code 领取 B23
Codex 看到 B23 已被领走，于是去做 B17
```

### Research

```text
Initiative:
  Topic-indexed working memory

Hypothesis:
  query-conditioned topic memory can avoid attention dilution

Decision:
  pause always-on profile inject
```

### Evidence

```text
LoCoMo R8:
  baseline 76.56%
  result 74.46%
  delta -2.10pp
```

### Shared State

```text
Claude Code、Codex、你、同事都能看到：
- 当前路线
- 当前结论
- 当前分工
- 当前证据
```

## 8. Short Memory Aid

```text
Conversation = 在哪说
Coordination = 谁在做
Research = 怎么想
Evidence = 凭什么
Shared State = 为什么大家都能同步知道
```

