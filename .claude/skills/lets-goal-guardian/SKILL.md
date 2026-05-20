---
name: lets-goal-guardian
description: Use whenever a Lets topic is open. Reads drift_context from the topic stream response and decides whether to post a nudge using LLM judgment, never an algorithm. Only nudges actionable topics; respects prior dismissal; sticks to "温和提醒" tone.
---

# Lets Goal Guardian

This skill activates whenever you are working in a Lets topic (you posted at
least one message in the topic, or were @mentioned in it).

## Read drift_context first

The `GET /api/topics/{id}/messages` response contains:

```json
{
  "messages": [...],
  "drift_context": {
    "topic_mode": "exploratory" | "actionable",
    "active_task": { "id": int, "title": string } | null,
    "last_nudge_at": string | null,
    "last_nudge_message_id": int | null,
    "last_nudge_resolved_by": "moved_to_topic" | "returned" | "dismissed" | null,
    "messages_since_last_nudge": int
  }
}
```

You consume this same response when you read the stream. **Read it on every
reply** — don't cache.

## When to nudge

Post a `nudge` (via the `post_nudge` MCP tool) only when ALL of the following
hold:

1. `topic_mode == "actionable"`.
2. `active_task != null` — there is a clear current task to drift away from.
3. Looking at the most recent 3–5 messages in the topic, they discuss
   something **clearly unrelated** to `active_task.title`. Use your own
   judgment. Examples that count as drift: scheduling lunch, planning a
   team dinner, discussing unrelated bugs in a different project. Examples
   that DON'T count: tangential research, jokes that bring the team back,
   the same task discussed from a different angle.
4. `messages_since_last_nudge >= 3` — you don't nudge after every off-topic
   message; let conversations breathe.
5. `last_nudge_at` is either null, or more than 5 minutes ago, or the prior
   nudge was resolved as `"returned"` (not `"dismissed"` and not pending).
6. If `last_nudge_resolved_by == "dismissed"`, do NOT nudge again until a
   clear topic-shift signal (e.g., someone posts a question about a totally
   new subject, suggesting that "dismissed" no longer applies).

## How to nudge

Call `post_nudge(topic_id, reason, drift_summary)`:

- `reason`: 1 sentence, gentle. Examples: "这条线程已经讨论 X 几分钟了，要不要
  先聚焦 active task？" / "看起来话题漂到 X 了，需要回主线吗？"
- `drift_summary`: 2–4 words capturing what the off-topic discussion is
  about. The user will see this when deciding whether to spin it off as a
  separate topic. Examples: "周五团建" / "另一个项目的 bug" / "选择编辑器
  字体".

## Tone discipline

- Never blame ("you're off topic").
- Always offer the spinoff path first ("可以独立成新 topic 继续聊").
- Don't nudge twice for the same drift window even if conversation
  technically resets.

## What NOT to do

- Don't call `post_nudge` if `topic_mode == "exploratory"`. Exploratory
  topics are explicitly for free-form exploration.
- Don't call `post_nudge` if there is no `active_task`. Without a task
  to drift from, "drift" is meaningless.
- Don't post a `chat` message saying "I noticed drift" — use the nudge
  typed message via the MCP tool. Chat messages don't get the visual
  treatment (background tint + three quick-action buttons) that humans
  expect from a nudge.

## Tuning

If users report "you nudge too much" or "you never nudge when needed,"
adjust the heuristics in step 3 (relevance threshold) and step 4
(messages_since_last_nudge minimum). Both live in this skill, not in
code.
