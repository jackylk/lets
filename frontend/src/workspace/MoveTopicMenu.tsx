import type { Workspace } from "../api/types";

interface Props {
  currentWorkspaceId: number;
  workspaces: Workspace[];
  onMove: (workspaceId: number) => void;
}

export function MoveTopicMenu({ currentWorkspaceId, workspaces, onMove }: Props) {
  const destinations = workspaces.filter((w) => w.id !== currentWorkspaceId);
  if (destinations.length === 0) {
    return <div className="text-xs text-text-dim">没有其他工作区</div>;
  }
  return (
    <div className="border border-border rounded bg-bg shadow p-1 min-w-[160px]">
      {destinations.map((w) => (
        <button
          key={w.id}
          type="button"
          onClick={() => onMove(w.id)}
          className="block w-full text-left text-sm px-3 py-1.5 hover:bg-hover rounded"
        >
          {w.name}
        </button>
      ))}
    </div>
  );
}
