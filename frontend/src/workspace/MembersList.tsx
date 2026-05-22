import type { WorkspaceMember } from "../api/types";

interface Props {
  members: WorkspaceMember[];
  onInvite: () => void;
  onInviteAgent?: () => void;
}

export function MembersList({ members, onInvite, onInviteAgent }: Props) {
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
            <div key={`a-${m.id}`} className="flex flex-col py-0.5">
              <span className="text-[12.5px] text-text">{m.role}</span>
              <span className="text-[10px] text-text-dim">
                agent · {m.started_by_name} 启动
              </span>
            </div>
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
