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
import { StreamProvider } from "../messages/StreamContext";
import { DiagramOverlay } from "../messages/DiagramOverlay";
import { Composer, type MentionCandidate, type MentionResolver } from "./Composer";
import { topicDisplayTitle } from "./topicSummary";
import type { MessageDTO, TaskTreeProposalMeta, WorkspaceMember } from "../api/types";

interface Props {
  topicId: number;
  workspaceMembers?: WorkspaceMember[];
}

export function TopicView({ topicId, workspaceMembers = [] }: Props) {
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

  // Build a mention resolver from workspace roster so people and agents can
  // be addressed before they have posted in this topic.
  const mentionCandidates: MentionCandidate[] = useMemo(() => {
    const out: MentionCandidate[] = [];
    const seen = new Set<string>();
    for (const m of workspaceMembers) {
      if (m.kind !== "agent" || m.deleted_at) continue;
      const online = Boolean(
        (agents.data ?? []).find((a) => a.agent_instance_id === m.id && a.is_online),
      );
      const key = m.role === "claude" ? "cc" : m.role === "codex" ? "cx" : m.role.toLowerCase();
      if (!seen.has(`agent:${key}`)) {
        seen.add(`agent:${key}`);
        out.push({
          key,
          label: `${m.display_name || m.role} · ${m.device_label || "device"}`,
          detail: `${online ? "online" : "offline"} · by ${m.owner_name}`,
          kind: "agent",
        });
      }
    }
    for (const m of workspaceMembers) {
      if (m.kind !== "human" || me.data?.human.id === m.id) continue;
      const key = m.name.toLowerCase();
      if (seen.has(`human:${key}`)) continue;
      seen.add(`human:${key}`);
      out.push({
        key,
        label: m.name,
        detail: "human",
        kind: "human",
      });
    }
    return out;
  }, [agents.data, me.data, workspaceMembers]);

  const resolver: MentionResolver = useMemo(() => {
    const lookup: Record<string, string> = {};
    for (const m of workspaceMembers) {
      if (m.kind === "human") {
        lookup[m.name.toLowerCase()] = `human:${m.id}`;
        continue;
      }
      if (m.deleted_at) continue;
      lookup[m.role.toLowerCase()] = `agent:${m.id}`;
      if (m.device_label) lookup[m.device_label.toLowerCase()] = `agent:${m.id}`;
      if (m.display_name) lookup[m.display_name.toLowerCase()] = `agent:${m.id}`;
      if (m.role === "claude") lookup["cc"] = `agent:${m.id}`;
      if (m.role === "codex") lookup["cx"] = `agent:${m.id}`;
    }
    // Topic participants are a fallback for older topics whose workspace
    // member query has not caught up yet.
    for (const h of participants.data?.humans ?? []) {
      lookup[h.name.toLowerCase()] ??= `human:${h.id}`;
    }
    return {
      resolveAddresses(mentions) {
        const out = new Set<string>();
        for (const m of mentions) {
          const address = lookup[m];
          if (address) out.add(address);
        }
        return [...out];
      },
      resolveHumanIds(mentions) {
        const out = new Set<number>();
        for (const m of mentions) {
          const address = lookup[m];
          if (address?.startsWith("human:")) {
            out.add(Number(address.slice("human:".length)));
          }
        }
        return [...out];
      },
    };
  }, [participants.data, workspaceMembers]);

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
              <ViewModeToggle />
            </div>
          }
        />
        <div className="flex-1 overflow-y-auto px-3 py-3 md:px-6 md:py-4">
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
        {/* Status strip lives below the composer so the user can see the agent's
            state while typing (eyes are already at the bottom of the screen). */}
        <AgentListenStatus messages={merged} workspaceMembers={workspaceMembers} />
      </div>
      <DiagramOverlay />
    </StreamProvider>
  );
}
