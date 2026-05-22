import { useState } from "react";
import { useTopicsInWorkspace } from "../api/queries";
import type { Workspace } from "../api/types";

interface Props {
  workspace: Workspace;
  onSelectTopic: (workspaceId: number, topicId: number) => void;
}

export function WorkspaceSection({ workspace, onSelectTopic }: Props) {
  const [open, setOpen] = useState(false);
  const { data: topics } = useTopicsInWorkspace(open ? workspace.id : null);

  return (
    <div className="px-3 py-1">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 text-xs text-text-dim hover:text-text w-full"
      >
        <span>{open ? "▾" : "▸"}</span>
        <span>{workspace.name}</span>
        {topics != null && (
          <span className="ml-auto font-mono">{topics.length}</span>
        )}
      </button>
      {open && topics && (
        <div className="pl-4 mt-1 space-y-0.5">
          {topics.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => onSelectTopic(workspace.id, t.id)}
              className="text-xs text-text-dim hover:text-text block w-full text-left py-0.5"
            >
              {t.title}
            </button>
          ))}
          {topics.length === 0 && (
            <div className="text-xs text-text-dim italic">还没有话题</div>
          )}
        </div>
      )}
    </div>
  );
}
