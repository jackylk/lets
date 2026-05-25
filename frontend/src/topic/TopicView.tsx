import { useEffect, useMemo, useRef, type ReactNode } from "react";
import {
  useTopicMessages, usePostMessage, useIdentityMe,
  useTopic, useTopicParticipants, useAllAgents,
  useAddTopicParticipant, useRemoveTopicParticipant,
  useUpdateTopicSettings,
  useUploadTopicAttachment,
} from "../api/queries";
import { useTopicStream } from "../api/sse";
import { TopicHeader } from "./TopicHeader";
import { Stream } from "./Stream";
import { ViewModeToggle } from "./ViewModeToggle";
import { AgentListenStatus } from "./AgentListenStatus";
import { StreamProvider } from "../messages/StreamContext";
import { DiagramOverlay } from "../messages/DiagramOverlay";
import { Composer, type MentionCandidate, type MentionResolver } from "./Composer";
import { topicDisplayTitle } from "./topicSummary";
import { topicMembersFromParticipants } from "./topicMembers";
import type { MessageDTO, TaskTreeProposalMeta, WorkspaceMember } from "../api/types";
import { agentShortName } from "../agent/display";
import { ApiError } from "../api/client";

interface Props {
  topicId: number;
  workspaceMembers?: WorkspaceMember[];
  onOpenResources?: () => void;
}

export function TopicView({ topicId, workspaceMembers = [], onOpenResources }: Props) {
  const me = useIdentityMe();
  const topic = useTopic(topicId);
  const participants = useTopicParticipants(topicId);
  const initial = useTopicMessages(topicId);
  const live = useTopicStream(topicId);
  const postMessage = usePostMessage(topicId);
  const uploadAttachment = useUploadTopicAttachment(topicId);
  const agents = useAllAgents();
  const scrollEndRef = useRef<HTMLDivElement | null>(null);
  const topicMembers = useMemo(
    () => topicMembersFromParticipants(workspaceMembers, participants.data, topic.data),
    [participants.data, topic.data, workspaceMembers],
  );

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
    const agentById = new Map<number, {
      id: number;
      role: string;
      device_label: string;
      display_name: string | null;
      human_id: number;
      deleted_at?: string | null;
    }>();
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
        device_label: a.device_label ?? "",
        display_name: a.display_name,
        deleted_at: a.deleted_at,
        human_id: 0,
      });
    }
    for (const a of agents.data ?? []) {
      agentById.set(a.agent_instance_id, {
        id: a.agent_instance_id,
        role: a.role,
        device_label: a.device_label,
        display_name: a.display_name,
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
      const displayName = agentShortName(m);
      const key = mentionKey(displayName);
      if (!seen.has(`agent:${key}`)) {
        seen.add(`agent:${key}`);
        out.push({
          key,
          label: displayName,
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
      lookup[mentionKey(agentShortName(m))] = `agent:${m.id}`;
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
          headerRight={<ViewModeToggle />}
          mobileHeaderRight={
            onOpenResources ? (
              <button
                type="button"
                onClick={onOpenResources}
                className="rounded-[3px] border border-border-soft bg-surface px-2.5 py-1 text-[13px] font-medium text-text hover:border-border"
              >
                AI 看板
              </button>
            ) : undefined
          }
          menu={
            <TopicParticipantsMenu
              topicId={topicId}
              topic={topic.data}
              participants={participants.data}
              workspaceMembers={workspaceMembers}
              currentHumanId={me.data?.human.id ?? null}
            />
          }
        />
        <div className="flex-1 overflow-y-auto px-3 py-3 md:px-6 md:py-4">
          {initial.isLoading && <div className="text-text-dim">加载中…</div>}
          {initial.isError && (
            <div className="text-text-dim">
              {initial.error instanceof ApiError && initial.error.status === 403
                ? "你不在这个话题中，请让管理员把你加入。"
                : "加载失败"}
            </div>
          )}
          <Stream messages={merged} directory={directory} topicId={topicId} />
          <div ref={scrollEndRef} />
        </div>
        <Composer
          statusSlot={
            <AgentListenStatus
              messages={merged}
              workspaceMembers={topicMembers}
              agentInterventionMode={topic.data?.agent_intervention_mode}
              showIdle
            />
          }
          onSend={send}
          onAttachFile={async (file) => {
            await uploadAttachment.mutateAsync({ file });
          }}
          resolver={resolver}
          mentionCandidates={mentionCandidates}
          disabled={postMessage.isPending}
          attachmentDisabled={uploadAttachment.isPending}
        />
      </div>
      <DiagramOverlay />
    </StreamProvider>
  );
}

function mentionKey(name: string) {
  return name.trim().toLowerCase().replace(/\s+/g, "-");
}

function TopicParticipantsMenu({
  topicId,
  topic,
  participants,
  workspaceMembers,
  currentHumanId,
}: {
  topicId: number;
  topic: ReturnType<typeof useTopic>["data"];
  participants: ReturnType<typeof useTopicParticipants>["data"];
  workspaceMembers: WorkspaceMember[];
  currentHumanId: number | null;
}) {
  const addParticipant = useAddTopicParticipant(topicId);
  const removeParticipant = useRemoveTopicParticipant(topicId);
  const updateTopic = useUpdateTopicSettings(topicId);
  const canManage = Boolean(participants?.can_manage) && !participants?.is_public;
  const isPublic = Boolean(participants?.is_public);

  const humanIds = new Set((participants?.humans ?? []).map((h) => h.id));
  const humanRoles = new Map((participants?.humans ?? []).map((h) => [h.id, h.role]));
  const explicitAgentIds = new Set(
    (participants?.agents ?? [])
      .filter((a) => a.is_explicit !== false)
      .map((a) => a.id),
  );
  const currentHumans = workspaceMembers
    .filter((m): m is Extract<WorkspaceMember, { kind: "human" }> => m.kind === "human" && humanIds.has(m.id))
    .map((m) => ({
      kind: "human" as const,
      id: m.id,
      label: m.name,
      removable: canManage && m.id !== currentHumanId && humanRoles.get(m.id) !== "owner",
    }));
  const currentAgents = workspaceMembers
    .filter((m): m is Extract<WorkspaceMember, { kind: "agent" }> =>
      m.kind === "agent" && explicitAgentIds.has(m.id),
    )
    .map((m) => ({
      kind: "agent" as const,
      id: m.id,
      label: agentShortName(m),
      removable: canManage && explicitAgentIds.has(m.id),
    }));
  const chips = [...currentHumans, ...currentAgents];
  const addableHumans = workspaceMembers.filter(
    (m): m is Extract<WorkspaceMember, { kind: "human" }> => m.kind === "human" && !humanIds.has(m.id),
  );
  const addableAgents = workspaceMembers.filter(
    (m): m is Extract<WorkspaceMember, { kind: "agent" }> =>
      m.kind === "agent" && !m.deleted_at && !explicitAgentIds.has(m.id),
  );

  function add(kind: "human" | "agent", id: number) {
    addParticipant.mutate({ participant_type: kind, participant_id: id });
  }

  function remove(kind: "human" | "agent", id: number) {
    removeParticipant.mutate({ participant_type: kind, participant_id: id });
  }

  return (
    <div className="flex flex-col gap-2">
      <ParticipantSection title="Agent 规则">
        <TopicSettingSelect
          label="插话"
          value={topic?.agent_intervention_mode ?? "auto"}
          disabled={!canManage || updateTopic.isPending}
          options={[
            ["auto", "自动"],
            ["mentions", "提到才回"],
            ["silent", "静默"],
          ]}
          onChange={(agent_intervention_mode) =>
            updateTopic.mutate({ agent_intervention_mode })
          }
        />
        <TopicSettingSelect
          label="上下文"
          value={topic?.shared_context_mode ?? "topic_with_files"}
          disabled={!canManage || updateTopic.isPending}
          options={[
            ["topic_with_files", "聊天 + 文件"],
            ["topic_only", "只看聊天"],
          ]}
          onChange={(shared_context_mode) =>
            updateTopic.mutate({ shared_context_mode })
          }
        />
      </ParticipantSection>
      <div className="border-t border-border-soft" />
      <ParticipantSection title={`话题成员 ${chips.length}`}>
        {isPublic && (
          <div className="px-2 pb-1 text-[12px] text-text-dim">
            全员话题自动包含工作区成员。
          </div>
        )}
        {chips.length === 0 ? (
          <div className="px-2 py-1 text-[12px] text-text-dim">暂无成员</div>
        ) : (
          chips.map((p) => (
            <div
              key={`${p.kind}:${p.id}`}
              className="flex min-w-0 items-center gap-2 rounded px-2 py-1.5 text-[12.5px] text-text-muted"
            >
              <span className="min-w-0 flex-1 truncate">
                {p.label}
                {p.kind === "agent" ? " · agent" : ""}
              </span>
              {p.removable && (
                <button
                  type="button"
                  aria-label={`移出 ${p.label}`}
                  onClick={() => remove(p.kind, p.id)}
                  className="shrink-0 rounded px-1.5 py-0.5 text-[11px] text-text-dim hover:bg-surface-hover hover:text-text"
                >
                  移出
                </button>
              )}
            </div>
          ))
        )}
      </ParticipantSection>
      {canManage && (
        <>
          <div className="border-t border-border-soft" />
          <ParticipantSection title="添加成员">
            {addableHumans.length === 0 ? (
              <div className="px-2 py-1 text-[12px] text-text-dim">成员都在话题里</div>
            ) : (
              addableHumans.map((m) => (
                <ParticipantAddButton key={m.id} onClick={() => add("human", m.id)}>
                  {m.name}
                </ParticipantAddButton>
              ))
            )}
          </ParticipantSection>
          <ParticipantSection title="添加 Agents">
            {addableAgents.length === 0 ? (
              <div className="px-2 py-1 text-[12px] text-text-dim">Agents 都在话题里</div>
            ) : (
              addableAgents.map((m) => (
                <ParticipantAddButton key={m.id} onClick={() => add("agent", m.id)}>
                  {agentShortName(m)}
                </ParticipantAddButton>
              ))
            )}
          </ParticipantSection>
        </>
      )}
      {!canManage && !isPublic && (
        <div className="px-2 py-1 text-[12px] text-text-dim">
          只有管理员可以增删话题成员。
        </div>
      )}
    </div>
  );
}

function ParticipantSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="mb-1 last:mb-0">
      <div className="px-2 pb-1 text-[11px] font-semibold text-text-dim">{title}</div>
      {children}
    </div>
  );
}

function TopicSettingSelect<T extends string>({
  label,
  value,
  options,
  disabled,
  onChange,
}: {
  label: string;
  value: T;
  options: Array<[T, string]>;
  disabled: boolean;
  onChange: (value: T) => void;
}) {
  return (
    <label className="mb-1 flex items-center gap-2 px-2 text-[12px] text-text-muted last:mb-0">
      <span className="w-12 shrink-0 text-text-dim">{label}</span>
      <select
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.currentTarget.value as T)}
        className="min-w-0 flex-1 rounded border border-border-soft bg-bg px-2 py-1 text-[12px] text-text outline-none disabled:opacity-50"
      >
        {options.map(([optionValue, optionLabel]) => (
          <option key={optionValue} value={optionValue}>
            {optionLabel}
          </option>
        ))}
      </select>
    </label>
  );
}

function ParticipantAddButton({ children, onClick }: { children: string; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex w-full items-center rounded px-2 py-1.5 text-left text-[12.5px] text-text-muted hover:bg-surface-hover hover:text-text"
    >
      <span className="truncate">{children}</span>
    </button>
  );
}
