import type { WorkspaceMember } from "../api/types";
import { agentShortName, roleTitle } from "../agent/display";

interface Props {
  workspaceName?: string;
  members: WorkspaceMember[];
  onInvite: () => void;
  onInviteAgent?: () => void;
  onSelectAgent?: (agentId: number) => void;
}

export function MembersList({ workspaceName, members, onInvite, onInviteAgent, onSelectAgent }: Props) {
  const humanCount = members.filter((m) => m.kind === "human").length;
  const agentCount = members.filter((m) => m.kind === "agent").length;
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
          return (
            <button
              key={`a-${m.id}`}
              type="button"
              onClick={() => onSelectAgent?.(m.id)}
              className="flex flex-col py-0.5 text-left rounded hover:bg-surface-hover"
            >
              <span className="text-[12.5px] text-text">
                {duplicateName ? `${name} · ${m.owner_name}` : name}
              </span>
              <span className="text-[10px] text-text-dim">
                {roleTitle(m.role)} · {m.owner_name} 管理
                {m.paused_at ? " · 已暂停" : ""}
                {m.deleted_at ? " · 已退役" : ""}
              </span>
            </button>
          );
        })}
        {members.length === 0 && (
          <div className="text-xs text-text-dim italic">暂无成员</div>
        )}
      </div>
      <div className="mt-2 flex flex-col gap-1 items-start">
        <button
          type="button"
          onClick={onInvite}
          className="text-xs text-text-dim hover:text-text"
        >
          ＋ 邀请人加入这个工作区
        </button>
        {onInviteAgent && (
          <button
            type="button"
            onClick={onInviteAgent}
            className="text-xs text-text-dim hover:text-text"
          >
            ＋ 邀请 agent 加入这个工作区
          </button>
        )}
      </div>
    </div>
  );
}
