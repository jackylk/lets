import type { WorkspaceMember } from "../api/types";

interface Props {
  members: WorkspaceMember[];
  onInvite: () => void;
  onInviteAgent?: () => void;
  onSelectAgent?: (agentId: number) => void;
}

export function MembersList({ members, onInvite, onInviteAgent, onSelectAgent }: Props) {
  return (
    <div className="px-3 py-2 border-t border-border">
      <div className="text-[10px] font-semibold uppercase tracking-wider text-text-dim mb-2">
        成员
      </div>
      <div className="flex flex-col gap-0.5">
        {members.map((m) =>
          m.kind === "human" ? (
            <div key={`h-${m.id}`} className="flex items-center gap-2 py-0.5">
              <span className="text-[12.5px] text-text truncate">{m.name}</span>
              {m.role === "owner" && (
                <span className="font-mono text-[10px] uppercase text-text-dim shrink-0">
                  owner
                </span>
              )}
            </div>
          ) : (
            <button
              key={`a-${m.id}`}
              type="button"
              onClick={() => onSelectAgent?.(m.id)}
              className="flex flex-col py-0.5 text-left rounded hover:bg-surface-hover"
            >
              <span className="text-[12.5px] text-text">
                {m.display_name || `${m.role}-${m.id}`}
              </span>
              <span className="text-[10px] text-text-dim">
                agent · 由 {m.owner_name} 管理
                {m.paused_at ? " · 已暂停" : ""}
                {m.deleted_at ? " · 已退役" : ""}
              </span>
            </button>
          ),
        )}
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
          ＋ 邀请成员
        </button>
        {onInviteAgent && (
          <button
            type="button"
            onClick={onInviteAgent}
            className="text-xs text-text-dim hover:text-text"
          >
            ＋ 邀请 agent
          </button>
        )}
      </div>
    </div>
  );
}
