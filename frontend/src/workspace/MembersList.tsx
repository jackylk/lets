import { useEffect, useMemo, useRef, useState } from "react";
import type { MessageDTO, WorkspaceMember, WorkspaceMemberAgent } from "../api/types";
import { agentShortName, roleTitle } from "../agent/display";
import { parseBackendTs } from "../lib/time";

interface Props {
  members: WorkspaceMember[];
  messages?: MessageDTO[];
  onInviteMember?: () => void;
  onInviteAgent?: () => void;
  canManageMembers?: boolean;
  onRemoveMember?: (humanId: number) => void | Promise<unknown>;
  onRemoveAgent?: (agentId: number) => void | Promise<unknown>;
  onSelectAgent?: (agentId: number) => void;
}

export function MembersList({
  members,
  messages = [],
  onInviteMember,
  onInviteAgent,
  canManageMembers = false,
  onRemoveMember,
  onRemoveAgent,
  onSelectAgent,
}: Props) {
  const [, force] = useState(0);
  const inviteMenuRef = useRef<HTMLDivElement>(null);
  const [inviteMenuOpen, setInviteMenuOpen] = useState(false);
  const visibleMembers = useMemo(
    () => members.filter((member) => member.kind !== "agent" || !member.deleted_at),
    [members],
  );
  useEffect(() => {
    const t = setInterval(() => force((x) => x + 1), 15_000);
    return () => clearInterval(t);
  }, []);
  useEffect(() => {
    if (!inviteMenuOpen) return;
    function onPointerDown(event: MouseEvent) {
      if (!inviteMenuRef.current?.contains(event.target as Node)) {
        setInviteMenuOpen(false);
      }
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setInviteMenuOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [inviteMenuOpen]);

  const humanCount = visibleMembers.filter((m) => m.kind === "human").length;
  const agentCount = visibleMembers.filter((m) => m.kind === "agent").length;
  const agentStatuses = useMemo(() => {
    const out = new Map<number, AgentTopicStatus>();
    for (const member of visibleMembers) {
      if (member.kind === "agent") out.set(member.id, topicStatusForAgent(member, messages));
    }
    return out;
  }, [visibleMembers, messages]);

  function removeHuman(id: number, name: string) {
    if (!window.confirm(`移除成员「${name}」？`)) return;
    void onRemoveMember?.(id);
  }

  function removeAgent(id: number, name: string) {
    if (!window.confirm(`移除 agent「${name}」？`)) return;
    void onRemoveAgent?.(id);
  }

  return (
    <div className="px-3 py-2 border-t border-border">
      <div className="mb-2">
        <div className="flex items-center gap-2">
          <div className="flex-1 text-[12px] font-semibold text-text-dim">
            当前工作区成员
          </div>
          {(onInviteMember || onInviteAgent) && (
            <div ref={inviteMenuRef} className="relative">
              <button
                type="button"
                aria-label="邀请工作区成员或 agent"
                title="邀请"
                onClick={() => setInviteMenuOpen((v) => !v)}
                className="grid h-6 w-6 place-items-center rounded-[3px] text-[16px] leading-none text-text-dim hover:bg-surface-hover hover:text-text"
              >
                +
              </button>
              {inviteMenuOpen && (
                <div className="absolute right-0 bottom-7 z-30 w-36 rounded-md border border-border bg-surface-elev p-1 shadow-[0_14px_40px_rgba(44,42,38,0.16)]">
                  {onInviteMember && (
                    <InviteMenuItem
                      onClick={() => {
                        setInviteMenuOpen(false);
                        onInviteMember();
                      }}
                    >
                      邀请成员
                    </InviteMenuItem>
                  )}
                  {onInviteAgent && (
                    <InviteMenuItem
                      onClick={() => {
                        setInviteMenuOpen(false);
                        onInviteAgent();
                      }}
                    >
                      邀请 agent
                    </InviteMenuItem>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
        <div className="mt-0.5 truncate text-[14px] text-text-muted">
          {humanCount} 人 · {agentCount} agent
        </div>
      </div>
      <div className="flex flex-col gap-0.5">
        {visibleMembers.map((m) => {
          if (m.kind === "human") {
            return (
            <div key={`h-${m.id}`} className="flex items-center gap-2 py-1">
              <PresenceDot online={Boolean(m.is_online)} label={`${m.name} ${m.is_online ? "在线" : "离线"}`} />
              <span className="text-[15px] text-text truncate">{m.name}</span>
              {m.role === "owner" && (
                <span className="font-mono text-[12px] uppercase text-text-dim shrink-0">
                  owner
                </span>
              )}
              {canManageMembers && m.role !== "owner" && onRemoveMember && (
                <button
                  type="button"
                  aria-label={`移除成员 ${m.name}`}
                  title="移除成员"
                  onClick={() => removeHuman(m.id, m.name)}
                  className="ml-auto shrink-0 rounded px-1.5 py-0.5 text-[12px] text-text-dim hover:bg-surface-hover hover:text-text"
                >
                  移除
                </button>
              )}
            </div>
            );
          }

          const name = agentShortName(m);
          const topicStatus = agentStatuses.get(m.id) ?? { label: "", tone: "idle" };
          const online = Boolean(m.is_online);
          const statusLabel = topicStatus.label || (online ? "在线" : "离线");
          const compactStatusLabel = compactAgentStatusLabel(statusLabel);
          const modelLabel = m.model?.trim() || "默认模型";
          const captionTitle = `${roleTitle(m.role)} · ${modelLabel} · ${statusLabel}`;
          return (
            <div
              key={`a-${m.id}`}
              className="flex w-full min-w-0 items-center gap-2 rounded py-1 hover:bg-surface-hover"
            >
              <button
                type="button"
                onClick={() => onSelectAgent?.(m.id)}
                className="flex min-w-0 flex-1 items-center gap-2 text-left"
              >
                <PresenceDot online={online} active={topicStatus.tone === "working"} label={`${name} ${online ? "在线" : "离线"}`} />
                <span className="max-w-[7rem] shrink-0 truncate text-[15px] text-text" title={name}>
                  {name}
                </span>
                <span className="min-w-0 flex-1 truncate text-[12px] text-text-dim" title={captionTitle}>
                  <span className={topicStatus.tone === "working" ? "text-accent-text" : ""}>
                    {compactStatusLabel}
                  </span>
                </span>
                {(m.paused_at || m.deleted_at) && (
                  <span className="shrink-0 text-[12px] text-text-dim">
                    {m.paused_at ? "已暂停" : "已退役"}
                  </span>
                )}
              </button>
              {canManageMembers && onRemoveAgent && (
                <button
                  type="button"
                  aria-label={`移除 agent ${name}`}
                  title="移除 agent"
                  onClick={() => removeAgent(m.id, name)}
                  className="shrink-0 rounded px-1.5 py-0.5 text-[12px] text-text-dim hover:bg-surface-hover hover:text-text"
                >
                  移除
                </button>
              )}
            </div>
          );
        })}
        {visibleMembers.length === 0 && (
          <div className="text-sm text-text-dim italic">暂无成员</div>
        )}
      </div>
      <PermissionsGuide />
    </div>
  );
}

function PermissionsGuide() {
  const rows = [
    ["Owner", "管理成员/agent；创建、归档、删除话题；查看全部话题"],
    ["GitHub 成员", "创建话题；参与公开话题和被加入的私有话题"],
    ["访客", "只参与可见话题；不能创建话题、邀请成员或管理 agent"],
    ["Agent", "只参与被加入的话题；按插话规则回复；可读取聊天和共享文件上下文；不能管理成员或创建话题"],
  ];
  return (
    <details className="mt-2 rounded border border-border-soft bg-surface-elev px-2 py-1.5">
      <summary className="cursor-pointer select-none text-[11.5px] font-medium text-text-dim">
        权限说明
      </summary>
      <div className="mt-1.5 overflow-x-auto">
        <table className="w-full text-left text-[11px] leading-snug text-text-muted">
          <thead className="text-text-dim">
            <tr>
              <th className="w-20 py-1 pr-2 font-medium">角色</th>
              <th className="py-1 font-medium">权限</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(([role, permissions]) => (
              <tr key={role} className="border-t border-border-soft align-top">
                <td className="py-1 pr-2 font-medium text-text">{role}</td>
                <td className="py-1">{permissions}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}

function InviteMenuItem({
  children,
  onClick,
}: {
  children: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex w-full items-center rounded px-2.5 py-1.5 text-left text-[13px] text-text-muted hover:bg-surface-hover hover:text-text"
    >
      {children}
    </button>
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

function compactAgentStatusLabel(label: string): string {
  if (label.startsWith("上次发言 ")) {
    return `发言${label.slice("上次发言 ".length).replace(/\s+/g, "")}`;
  }
  return label.replace(/\s+/g, "");
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
