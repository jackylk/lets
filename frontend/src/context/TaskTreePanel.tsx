import { useState } from "react";
import { cn } from "../lib/cn";
import {
  useAddTaskItem,
  useTopicTaskTree,
  useUpdateTaskItem,
} from "../api/taskTreeQueries";
import type { TaskItemDTO } from "../api/taskTreeTypes";

interface Props {
  topicId: number;
}

export function TaskTreePanel({ topicId }: Props) {
  const tree = useTopicTaskTree(topicId);
  const update = useUpdateTaskItem(topicId);
  const add = useAddTaskItem(topicId);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const [adding, setAdding] = useState(false);
  const [newTitle, setNewTitle] = useState("");

  if (tree.isLoading || !tree.data) {
    return <div className="text-text-dim text-sm">加载中…</div>;
  }
  if (!tree.data.tree) {
    return (
      <div className="border border-dashed border-border rounded p-3 text-center text-text-dim text-sm">
        尚未设定 task tree
      </div>
    );
  }

  const treeId = tree.data.tree.id;
  const items = tree.data.items;
  const roots = items.filter((i) => i.parent_item_id === null);
  const doneCount = items.filter((i) => i.status === "done").length;

  function toggleExpand(id: number) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleDone(item: TaskItemDTO) {
    update.mutate({
      id: item.id,
      status: item.status === "done" ? "pending" : "done",
    });
  }

  function submitAdd() {
    if (!newTitle.trim()) return;
    add.mutate({ task_tree_id: treeId, title: newTitle.trim() });
    setNewTitle("");
    setAdding(false);
  }

  function renderItem(item: TaskItemDTO, depth: number) {
    const children = items.filter((i) => i.parent_item_id === item.id);
    const hasChildren = children.length > 0;
    const isExpanded = expanded.has(item.id);
    return (
      <div key={item.id}>
        <div
          className="flex items-center gap-2 text-[12.5px] py-0.5"
          style={{ paddingLeft: depth * 12 }}
        >
          {hasChildren ? (
            <button
              type="button"
              aria-label={`expand-${item.id}`}
              onClick={() => toggleExpand(item.id)}
              className="text-[10px] text-text-dim w-3"
            >
              {isExpanded ? "▾" : "▸"}
            </button>
          ) : (
            <span className="w-3" />
          )}
          <input
            type="checkbox"
            checked={item.status === "done"}
            onChange={() => toggleDone(item)}
            aria-label={item.title}
            className="cursor-pointer"
          />
          <span
            className={cn(
              "flex-1 truncate",
              item.status === "done" && "text-text-dim line-through",
            )}
          >
            {item.title}
          </span>
        </div>
        {hasChildren && isExpanded && (
          <div>{children.map((c) => renderItem(c, depth + 1))}</div>
        )}
      </div>
    );
  }

  return (
    <div className="border border-border-soft rounded-lg bg-surface-elev p-3 flex flex-col gap-2">
      <div className="flex items-baseline justify-between">
        <span className="font-semibold text-[13px]">研讨 PPT 终版</span>
        <span className="font-mono text-[11px] text-text-dim">
          {doneCount} / {items.length} done
        </span>
      </div>
      <div className="flex flex-col">
        {roots.map((r) => renderItem(r, 0))}
      </div>
      {adding ? (
        <input
          autoFocus
          placeholder="输入新任务，回车保存"
          value={newTitle}
          onChange={(e) => setNewTitle(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") submitAdd();
            if (e.key === "Escape") setAdding(false);
          }}
          className="text-[12px] px-2 py-1 border border-border rounded bg-bg"
        />
      ) : (
        <button
          type="button"
          onClick={() => setAdding(true)}
          className="text-[11px] text-text-dim hover:text-text text-left"
        >
          + 加任务
        </button>
      )}
    </div>
  );
}
