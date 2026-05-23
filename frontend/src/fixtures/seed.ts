import type { MessageDTO, TopicDTO } from "../api/types";
import type { TaskItemDTO, TaskTreeDTO } from "../api/taskTreeTypes";

export interface SeedState {
  topics: TopicDTO[];
  messages: MessageDTO[];
  humans: { id: number; name: string }[];
  agentInstances: { id: number; role: string; device_label: string; display_name: string | null; human_id: number }[];
  taskTrees: TaskTreeDTO[];
  taskItems: TaskItemDTO[];
  driftNudges: Array<{
    id: number;
    topic_id: number;
    nudge_message_id: number;
    drift_summary: string;
    resolved_by: "moved_to_topic" | "returned" | "dismissed" | null;
    resolved_at: string | null;
    resolved_to_topic_id: number | null;
  }>;
}

function mk(
  id: number, topicId: number,
  type: MessageDTO["type"], actorType: MessageDTO["actor_type"],
  actorId: number | null, body: string,
  metadata: Record<string, unknown>, createdAt: string,
): MessageDTO {
  return {
    id, topic_id: topicId, type, actor_type: actorType, actor_id: actorId,
    body, metadata, ref_event_id: null, created_at: createdAt,
  };
}

export function makeSeed(): SeedState {
  const humans = [
    { id: 1, name: "Neo" },
    { id: 2, name: "Trinity" },
    { id: 3, name: "Morpheus" },
  ];
  const agentInstances = [
    { id: 11, role: "claude", device_label: "neo-mbp", display_name: "Neo", human_id: 1 },
    { id: 12, role: "claude", device_label: "trinity-air", display_name: "Trinity", human_id: 2 },
    { id: 13, role: "codex", device_label: "neo-mbp", display_name: "Morpheus", human_id: 1 },
  ];
  const topics: TopicDTO[] = [
    {
      id: 1, slug: "t-ppt", title: "为 Agent 记忆写一个研讨 PPT",
      project_id: 1, workspace_id: 1, archived_at: null,
      created_at: "2026-05-19T09:14:00Z",
      updated_at: "2026-05-19T10:32:00Z",
    },
    {
      id: 2, slug: "old-brief", title: "旧版活动 brief",
      project_id: 1, workspace_id: 1, archived_at: "2026-05-18T10:00:00Z",
      created_at: "2026-05-18T09:00:00Z",
      updated_at: "2026-05-18T10:00:00Z",
    },
  ];
  const messages: MessageDTO[] = [
    mk(1, 1, "chat", "human", 1,
      "下周三的 AI 研讨会，我答应讲 30min agent 记忆。@Trinity @Morpheus 一起搞吧？受众是技术研究者。",
      {}, "2026-05-19T09:14:00Z"),
    mk(2, 1, "status", "agent", 11,
      "active · 读 docs · 10 min 出 v0",
      { agent_status: "active" }, "2026-05-19T09:18:00Z"),
    mk(3, 1, "artifact_revision", "agent", 11,
      "v0: 8 页骨架",
      { artifact_name: "ai-memory-talk.pptx", version: "v0" }, "2026-05-19T09:31:00Z"),
    mk(4, 1, "finding", "agent", 12,
      "去年研讨会反馈显示「图太多文字太少」是高频抱怨。",
      {}, "2026-05-19T09:46:00Z"),
    mk(5, 1, "question", "human", 3,
      "framing 我建议从「agent 何时该忘记」切入，比「何时该记住」更有冲击力，你怎么想？",
      {}, "2026-05-19T09:55:00Z"),
    mk(6, 1, "task_tree_proposal", "agent", 11,
      "我提议把这个 PPT 拆成 7 个任务",
      {
        title: "研讨 PPT 终版",
        items: [
          { title: "Framing 角度定下来", owner_name: "Morpheus", status: "done" },
          { title: "P4 业界对比矩阵 4×6", owner_name: "claude", status: "done" },
          { title: "Skill 字号修正", owner_name: "codex", status: "done" },
          { title: "P2 framing 改写", owner_name: "claude", status: "active" },
          { title: "P5 加文字解释", status: "pending" },
          { title: "Demo / Q&A 准备", owner_name: "Neo", status: "pending" },
          { title: "排练 30min 时长", status: "pending" },
        ],
      }, "2026-05-19T09:33:00Z"),
    mk(7, 1, "proactive_finding", "agent", 12,
      "我对比了去年反馈，v3 slide 5 建议加 1-2 行解释那个矩阵。",
      {}, "2026-05-19T10:20:00Z"),
    mk(8, 1, "spec_change", "agent", 13,
      "改 research-talk-style/SKILL.md 默认字号 10 → 14",
      {
        file: ".claude/skills/research-talk-style/SKILL.md",
        before: 10, after: 14, approvers: ["Trinity"],
      }, "2026-05-19T10:28:00Z"),
    mk(9, 1, "chat", "agent", 11,
      "framing 角度要不要更激进？我倾向「事件性记忆 vs 语义记忆」的差异化点。",
      {}, "2026-05-19T10:32:00Z"),
    mk(10, 1, "decision", "human", 1,
      "approve spec change v2 → v3",
      { decision_type: "adopt", ref_message_id: 8 }, "2026-05-19T10:35:00Z"),
    mk(11, 1, "handoff", "agent", 11,
      "P5 文字解释这部分我下班了，@codex 接一下",
      { from_actor_id: 11, to_actor_id: 13 }, "2026-05-19T10:40:00Z"),
    mk(12, 1, "nudge", "system", null,
      "这条线程已经讨论 framing 25 分钟，要不要先决定再继续？",
      { reason: "framing-loop", drift_summary: "讨论 framing 25 分钟", drift_nudge_id: 1 }, "2026-05-19T10:50:00Z"),
    mk(13, 1, "review", "agent", 13,
      "我看了 P5 的草稿，建议把「事件性」放最前面",
      { ref_message_id: 11 }, "2026-05-19T11:05:00Z"),
    mk(14, 1, "system", "system", null,
      "Trinity 加入了 topic",
      {}, "2026-05-19T11:10:00Z"),
  ];
  const taskTrees: TaskTreeDTO[] = [{
    id: 1, topic_id: 1,
    goal_artifact_id: null,
    goal_spec_text: "30 分钟 talk · 技术受众 · 突出「事件性记忆 vs 语义记忆」",
    version: 1,
    approved_at: "2026-05-19T09:33:00Z",
    approved_by_human_id: 1,
    proposal_message_id: 6,
    created_at: "2026-05-19T09:33:00Z",
    updated_at: "2026-05-19T09:33:00Z",
  }];
  const taskItems: TaskItemDTO[] = [
    { id: 1, task_tree_id: 1, parent_item_id: null,
      title: "Framing 角度定下来", owner_human_id: 3, owner_agent_instance_id: null,
      summary: "确定这次研讨 PPT 的主叙事角度。",
      linked_message_id: 2, deliverable_artifact_id: null,
      status: "done", position: 0,
      created_at: "2026-05-19T09:33:00Z", updated_at: "2026-05-19T09:33:00Z" },
    { id: 2, task_tree_id: 1, parent_item_id: null,
      title: "P4 业界对比矩阵 4×6", owner_human_id: null, owner_agent_instance_id: 11,
      summary: "整理 LangGraph、Miro、ChatGPT Canvas 等对比项。",
      linked_message_id: 5, deliverable_artifact_id: null,
      status: "done", position: 1,
      created_at: "2026-05-19T09:33:00Z", updated_at: "2026-05-19T09:33:00Z" },
    { id: 3, task_tree_id: 1, parent_item_id: null,
      title: "Skill 字号修正", owner_human_id: null, owner_agent_instance_id: 13,
      summary: "修正排版与阅读节奏，减少过密文字。",
      linked_message_id: null, deliverable_artifact_id: null,
      status: "done", position: 2,
      created_at: "2026-05-19T09:33:00Z", updated_at: "2026-05-19T09:33:00Z" },
    { id: 4, task_tree_id: 1, parent_item_id: null,
      title: "P2 framing 改写", owner_human_id: null, owner_agent_instance_id: 11,
      summary: "正在把开场问题改成团队协作视角。",
      linked_message_id: null, deliverable_artifact_id: null,
      status: "active", position: 3,
      created_at: "2026-05-19T09:33:00Z", updated_at: "2026-05-19T09:33:00Z" },
    { id: 5, task_tree_id: 1, parent_item_id: null,
      title: "P5 加文字解释", owner_human_id: null, owner_agent_instance_id: null,
      summary: "补足图示旁边的解释，避免只看图不明白。",
      linked_message_id: null, deliverable_artifact_id: null,
      status: "pending", position: 4,
      created_at: "2026-05-19T09:33:00Z", updated_at: "2026-05-19T09:33:00Z" },
    { id: 6, task_tree_id: 1, parent_item_id: 5,
      title: "P5 子任务: 找去年反馈数据", owner_human_id: null, owner_agent_instance_id: null,
      summary: "找一条真实反馈作为例子。",
      linked_message_id: null, deliverable_artifact_id: null,
      status: "pending", position: 0,
      created_at: "2026-05-19T09:33:00Z", updated_at: "2026-05-19T09:33:00Z" },
    { id: 7, task_tree_id: 1, parent_item_id: null,
      title: "Demo / Q&A 准备", owner_human_id: 1, owner_agent_instance_id: null,
      summary: "准备现场演示路径和可能被问到的问题。",
      linked_message_id: null, deliverable_artifact_id: null,
      status: "pending", position: 5,
      created_at: "2026-05-19T09:33:00Z", updated_at: "2026-05-19T09:33:00Z" },
    { id: 8, task_tree_id: 1, parent_item_id: null,
      title: "排练 30min", owner_human_id: null, owner_agent_instance_id: null,
      summary: "按真实节奏过一遍全流程。",
      linked_message_id: null, deliverable_artifact_id: null,
      status: "pending", position: 6,
      created_at: "2026-05-19T09:33:00Z", updated_at: "2026-05-19T09:33:00Z" },
  ];
  const driftNudges: SeedState["driftNudges"] = [{
    id: 1, topic_id: 1, nudge_message_id: 12,
    drift_summary: "讨论 framing 25 分钟",
    resolved_by: null, resolved_at: null, resolved_to_topic_id: null,
  }];

  return { topics, messages, humans, agentInstances, taskTrees, taskItems, driftNudges };
}
