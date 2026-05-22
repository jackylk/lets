import type { Workspace } from "../api/types";

interface Props {
  workspaces: Workspace[];
  activeId: number;
  onSelect: (id: number) => void;
  onCreate: () => void;
}

export function WorkspaceSwitcher({ workspaces, activeId, onSelect, onCreate }: Props) {
  const active = workspaces.find((w) => w.id === activeId);
  const others = workspaces.filter((w) => w.id !== activeId).slice(0, 2);
  return (
    <div className="flex items-center gap-1 px-3 py-2 border-b border-border">
      <button
        type="button"
        className="font-[var(--font-display)] text-sm text-text px-2 py-1 rounded hover:bg-surface-hover"
      >
        {active?.name ?? "—"} ▾
      </button>
      {others.map((w) => (
        <button
          key={w.id}
          type="button"
          onClick={() => onSelect(w.id)}
          className="text-xs text-text-dim hover:text-text px-2 py-1 rounded hover:bg-surface-hover"
        >
          {w.name}
        </button>
      ))}
      <button
        type="button"
        onClick={onCreate}
        title="新建工作区"
        aria-label="新建工作区"
        className="text-xs text-text-dim hover:text-text px-2 py-1 rounded hover:bg-surface-hover ml-auto"
      >
        ＋
      </button>
    </div>
  );
}
