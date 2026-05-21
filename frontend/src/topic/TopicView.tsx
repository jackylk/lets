import { useEffect, useMemo, useRef } from "react";
import {
  useTopicMessages, usePostMessage, useIdentityMe,
  useTopic, useTopicParticipants, useAllAgents,
} from "../api/queries";
import { useTopicStream } from "../api/sse";
import { TopicHeader } from "./TopicHeader";
import { AgentListenStatus } from "./AgentListenStatus";
import { Stream } from "./Stream";
import { ViewModeToggle } from "./ViewModeToggle";
import { ExportSpecButton } from "./ExportSpecButton";
import { StreamProvider } from "../messages/StreamContext";
import { DiagramOverlay } from "../messages/DiagramOverlay";
import { Composer, type MentionCandidate, type MentionResolver } from "./Composer";
import { topicDisplayTitle } from "./topicSummary";
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
  const agents = useAllAgents();
  const scrollEndRef = useRef<HTMLDivElement | null>(null);

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
    const humanById = new Map<number, { id: number; name: string }>();
    const agentById = new Map<number, { id: number; role: string; device_label: string; human_id: number }>();
    if (me.data?.human) {
      humanById.set(me.data.human.id, {
        id: me.data.human.id,
        name: me.data.human.name,
      });
    }
    for (const h of p?.humans ?? []) {
      humanById.set(h.id, { id: h.id, name: h.name });
    }
    for (const a of p?.agents ?? []) {
      agentById.set(a.id, {
        id: a.id,
        role: a.role,
        device_label: a.device_label,
        human_id: 0,
      });
    }
    for (const a of agents.data ?? []) {
      agentById.set(a.agent_instance_id, {
        id: a.agent_instance_id,
        role: a.role,
        device_label: a.device_label,
        human_id: a.human_id,
      });
    }
    return {
      humans: [...humanById.values()],
      agentInstances: [...agentById.values()],
    };
  }, [agents.data, me.data, participants.data]);

  // Build a mention resolver: @cc / @codex / @<role> / @<device> / @<human> → human_id list.
  const mentionCandidates: MentionCandidate[] = useMemo(() => {
    const out: MentionCandidate[] = [];
    const seen = new Set<string>();
    for (const a of agents.data ?? []) {
      if (!a.is_online) continue;
      const key = a.role === "claude" ? "cc" : a.role === "codex" ? "cx" : a.role.toLowerCase();
      if (!seen.has(`agent:${key}`)) {
        seen.add(`agent:${key}`);
        out.push({
          key,
          label: `${a.role} · ${a.device_label}`,
          detail: a.is_online ? "online" : "offline",
          kind: "agent",
        });
      }
    }
    for (const h of participants.data?.humans ?? []) {
      if (me.data?.human.id === h.id) continue;
      const key = h.name.toLowerCase();
      if (seen.has(`human:${key}`)) continue;
      seen.add(`human:${key}`);
      out.push({
        key,
        label: h.name,
        detail: "human",
        kind: "human",
      });
    }
    return out;
  }, [agents.data, me.data, participants.data]);

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

  const title = topicDisplayTitle(topic.data, merged) || (topic.isLoading ? "" : `Topic #${topicId}`);

  useEffect(() => {
    scrollEndRef.current?.scrollIntoView?.({ block: "end" });
  }, [topicId, merged.length]);

  return (
    <StreamProvider messages={merged} directory={directory} topicId={topicId}>
      <div className="flex flex-col h-full">
        <TopicHeader
          title={title}
          goal={goal}
          headerRight={
            <div className="flex items-center gap-2">
              <ExportSpecButton topicId={topicId} />
              <ViewModeToggle />
            </div>
          }
        />
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {initial.isLoading && <div className="text-text-dim">加载中…</div>}
          {initial.isError && <div className="text-text-dim">加载失败</div>}
          <Stream messages={merged} directory={directory} topicId={topicId} />
          <div ref={scrollEndRef} />
        </div>
        <Composer
          onSend={send}
          resolver={resolver}
          mentionCandidates={mentionCandidates}
          disabled={postMessage.isPending}
        />
        {/* Status strip lives below the composer so the user can see CC's
            state while typing (eyes are already at the bottom of the screen). */}
        <AgentListenStatus messages={merged} />
      </div>
      <DiagramOverlay />
    </StreamProvider>
  );
}
