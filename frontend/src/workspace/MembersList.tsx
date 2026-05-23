import { useEffect, useMemo, useState } from "react";
import type { MessageDTO, WorkspaceMember, WorkspaceMemberAgent } from "../api/types";
import { agentShortName, roleTitle } from "../agent/display";
import { parseBackendTs } from "../lib/time";

interface Props {
  workspaceName?: string;
  members: WorkspaceMember[];
  messages?: MessageDTO[];
  onSelectAgent?: (agentId: number) => void;
}

export function MembersList({ workspaceName, members, messages = [], onSelectAgent }: Props) {
  const [, force] = useState(0);
  useEffect(() => {
    const t = setInterval(() => force((x) => x + 1), 15_000);
    return () => clearInterval(t);
  }, []);

  const humanCount = members.filter((m) => m.kind === "human").length;
  const agentCount = members.filter((m) => m.kind === "agent").length;
  const agentStatuses = useMemo(() => {
    const out = new Map<number, AgentTopicStatus>();
    for (const member of members) {
      if (member.kind === "agent") out.set(member.id, topicStatusForAgent(member, messages));
    }
    return out;
  }, [members, messages]);
  const agentNameCounts = new Map<string, number>();
  for (const member of members) {
    if (member.kind !== "agent") continue;
    const name = agentShortName(member);
    agentNameCounts.set(name, (agentNameCounts.get(name) ?? 0) + 1);
  }

  return (
    <div className="px-3 py-2 border-t border-border">
      <div className="mb-2">
        <div className="text-[10px] font-semibold uppercase tracking-wider text-text-dim">
          当前工作区成员
        </div>
        {workspaceName && (
          <div className="mt-0.5 truncate text-[12px] text-text-muted">
            {workspaceName} · {humanCount} 人 · {agentCount} agent
          </div>
        )}
      </div>
      <div className="flex flex-col gap-0.5">
        {members.map((m) => {
          if (m.kind === "human") {
            return (
            <div key={`h-${m.id}`} className="flex items-center gap-2 py-0.5">
              <PresenceDot online={Boolean(m.is_online)} label={`${m.name} ${m.is_online ? "在线" : "离线"}`} />
              <span className="text-[12.5px] text-text truncate">{m.name}</span>
              {m.role === "owner" && (
                <span className="font-mono text-[10px] uppercase text-text-dim shrink-0">
                  owner
                </span>
              )}
            </div>
            );
          }

          const name = agentShortName(m);
          const duplicateName = (agentNameCounts.get(name) ?? 0) > 1;
          const topicStatus = agentStatuses.get(m.id) ?? { label: "", tone: "idle" };
          const online = Boolean(m.is_online);
          return (
            <button
              key={`a-${m.id}`}
              type="button"
              onClick={() => onSelectAgent?.(m.id)}
              className="flex flex-col py-0.5 text-left rounded hover:bg-surface-hover"
            >
              <span className="flex items-center gap-2 text-[12.5px] text-text">
                <PresenceDot online={online} active={topicStatus.tone === "working"} label={`${name} ${online ? "在线" : "离线"}`} />
                <span>{duplicateName ? `${name} · ${m.owner_name}` : name}</span>
              </span>
              <span className="ml-3.5 text-[10px] text-text-dim">
                {roleTitle(m.role)} · {m.owner_name} 管理
                {m.paused_at ? " · 已暂停" : ""}
                {m.deleted_at ? " · 已退役" : ""}
                {" · "}
                <span className={topicStatus.tone === "working" ? "text-accent-text" : ""}>
                  {topicStatus.label || (online ? "在线" : "离线")}
                </span>
              </span>
            </button>
          );
        })}
        {members.length === 0 && (
          <div className="text-xs text-text-dim italic">暂无成员</div>
        )}
      </div>
    </div>
  );
}

type AgentTopicStatus = {
  label: string;
  tone: "idle" | "working";
};

function topicStatusForAgent(agent: WorkspaceMemberAgent, messages: MessageDTO[]): AgentTopicStatus {
  let lastHuman: MessageDTO | null = null;
  let lastActivityAt: string | null = null;
  let lastReplyAt: string | null = null;
  let pendingStatus: MessageDTO | null = null;

  for (const m of messages) {
    if (m.actor_type === "human") {
      if (!lastHuman || m.created_at > lastHuman.created_at) lastHuman = m;
      continue;
    }
    if (m.actor_type !== "agent" || m.actor_id !== agent.id) continue;
    if (!lastActivityAt || m.created_at > lastActivityAt) lastActivityAt = m.created_at;
    if (m.type === "chat" || m.type === "finding") {
      if (!lastReplyAt || m.created_at > lastReplyAt) lastReplyAt = m.created_at;
    }
    if (m.type === "status") {
      const meta = (m.metadata as Record<string, unknown> | null) ?? {};
      if (meta.phase === "thinking") pendingStatus = m;
    }
  }

  if (pendingStatus && (!lastReplyAt || pendingStatus.created_at > lastReplyAt)) {
    return { label: "思考中", tone: "working" };
  }

  if (
    lastHuman &&
    (!lastActivityAt || lastHuman.created_at > lastActivityAt) &&
    secsSince(lastHuman.created_at) < 8
  ) {
    const addressed = String(lastHuman.addressed_to ?? "").split(",").map((p) => p.trim());
    if (addressed.includes(`agent:${agent.id}`) || (lastHuman.body || "").includes("@")) {
      return { label: "即将介入", tone: "working" };
    }
  }

  if (lastReplyAt) return { label: `上次发言 ${ago(lastReplyAt)}`, tone: "idle" };
  return { label: "", tone: "idle" };
}

function ago(iso: string): string {
  const secs = secsSince(iso);
  if (secs < 60) return "刚刚";
  const mins = secs / 60;
  if (mins < 60) return `${Math.round(mins)} 分钟前`;
  const hours = mins / 60;
  if (hours < 24) return `${Math.round(hours)} 小时前`;
  return `${Math.round(hours / 24)} 天前`;
}

function secsSince(iso: string): number {
  return Math.max(0, (Date.now() - parseBackendTs(iso).getTime()) / 1000);
}

function PresenceDot({ online, active, label }: { online: boolean; active?: boolean; label: string }) {
  return (
    <span
      aria-label={label}
      title={label}
      className={
        "h-2 w-2 shrink-0 rounded-full border " +
        (active
          ? "border-accent bg-accent shadow-[0_0_0_3px_color-mix(in_oklch,var(--color-accent)_25%,transparent)] animate-pulse"
          : online
          ? "border-[#22784f] bg-[#2fa66a]"
          : "border-border bg-text-dim/30")
      }
    />
  );
}
