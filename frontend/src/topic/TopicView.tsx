import { useMemo } from "react";
import {
  useTopicMessages, usePostMessage, useIdentityMe,
  useTopic, useTopicParticipants, useAllAgents,
} from "../api/queries";
import { useTopicStream } from "../api/sse";
import { TopicHeader } from "./TopicHeader";
import { Stream } from "./Stream";
import { Composer, type MentionResolver } from "./Composer";
import type { MessageDTO, TaskTreeProposalMeta } from "../api/types";

interface Props {
  topicId: number;
}

export function TopicView({ topicId }: Props) {
  const me = useIdentityMe();
  const topic = useTopic(topicId);
  const participants = useTopicParticipants(topicId);
  const initial = useTopicMessages(topicId);
  const live = useTopicStream(topicId);
  const postMessage = usePostMessage(topicId);

  const merged: MessageDTO[] = useMemo(() => {
    const base = initial.data?.messages ?? [];
    if (live.messages.length === 0) return base;
    const seen = new Set(base.map((m) => m.id));
    const extra = live.messages.filter((m) => !seen.has(m.id));
    return [...base, ...extra];
  }, [initial.data, live.messages]);

  // Derive a goal-progress summary from the most recent task_tree_proposal
  // in this topic. If none, no goal chip is rendered.
  const goal = useMemo(() => {
    const proposals = merged.filter((m) => m.type === "task_tree_proposal");
    const latest = proposals[proposals.length - 1];
    if (!latest) return undefined;
    const meta = latest.metadata as unknown as TaskTreeProposalMeta;
    if (!meta || !Array.isArray(meta.items)) return undefined;
    const doneCount = meta.items.filter((it) => it.status === "done").length;
    const totalCount = meta.items.length;
    const current = meta.items.find((it) => it.status === "active")?.title ?? null;
    return { doneCount, totalCount, currentTaskTitle: current };
  }, [merged]);

  // Build a real actor directory from /api/topics/{id}/participants
  const directory = useMemo(() => {
    const p = participants.data;
    if (!p) return { humans: [], agentInstances: [] };
    return {
      humans: p.humans.map((h) => ({ id: h.id, name: h.name })),
      agentInstances: p.agents.map((a) => ({
        id: a.id,
        role: a.role,
        device_label: a.device_label,
        human_id: 0, // not currently needed by Stream rendering
      })),
    };
  }, [participants.data]);

  // Build a mention resolver: @cc / @codex / @<role> / @<device> / @<human> → human_id list.
  const agents = useAllAgents();
  const resolver: MentionResolver = useMemo(() => {
    const lookup: Record<string, number> = {};
    // Humans in the topic
    for (const h of participants.data?.humans ?? []) {
      lookup[h.name.toLowerCase()] = h.id;
    }
    // Agents in the topic — @cc / @codex / @<role> / @<device> all map to
    // the agent's human (the runner triggers on human_id match)
    for (const a of agents.data ?? []) {
      lookup[a.role.toLowerCase()] = a.human_id;
      lookup[a.device_label.toLowerCase()] = a.human_id;
      // Short aliases the user is likely to type
      if (a.role === "claude") lookup["cc"] = a.human_id;
      if (a.role === "codex") lookup["cx"] = a.human_id;
    }
    return {
      resolveHumanIds(mentions) {
        const out = new Set<number>();
        for (const m of mentions) {
          const id = lookup[m];
          if (id != null) out.add(id);
        }
        return [...out];
      },
    };
  }, [participants.data, agents.data]);

  function send(msg: { body: string; addressedTo: string | null }) {
    if (!me.data) return;
    postMessage.mutate({
      topic_id: topicId,
      type: "chat",
      actor_type: "human",
      actor_id: me.data.human.id,
      body: msg.body,
      addressed_to: msg.addressedTo,
    });
  }

  const title = topic.data?.title ?? (topic.isLoading ? "" : `Topic #${topicId}`);

  return (
    <div className="flex flex-col h-full">
      <TopicHeader title={title} goal={goal} />
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {initial.isLoading && <div className="text-text-dim">加载中…</div>}
        {initial.isError && <div className="text-text-dim">加载失败</div>}
        <Stream messages={merged} directory={directory} />
      </div>
      <Composer onSend={send} resolver={resolver} disabled={postMessage.isPending} />
    </div>
  );
}
