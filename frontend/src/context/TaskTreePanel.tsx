import { useMemo, useState } from "react";
import { cn } from "../lib/cn";
import {
  useAddTaskItem,
  useAdoptGoalProposal,
  useTopicTaskTree,
  useUpdateTaskItem,
} from "../api/taskTreeQueries";
import type { TaskItemDTO } from "../api/taskTreeTypes";

interface Props {
  topicId: number;
}

const statusLabel: Record<TaskItemDTO["status"], string> = {
  pending: "待探索",
  active: "探索中",
  done: "已交付",
};

export function TaskTreePanel({ topicId }: Props) {
  const tree = useTopicTaskTree(topicId);
  const createTree = useAdoptGoalProposal(topicId);
  const update = useUpdateTaskItem(topicId);
  const add = useAddTaskItem(topicId);
  const [addingParentId, setAddingParentId] = useState<number | null | "root">(null);
  const [newTitle, setNewTitle] = useState("");
  const [newSummary, setNewSummary] = useState("");

  const items = tree.data?.items ?? [];
  const childrenByParent = useMemo(() => {
    const groups = new Map<number | null, TaskItemDTO[]>();
    for (const item of items) {
      const key = item.parent_item_id;
      groups.set(key, [...(groups.get(key) ?? []), item]);
    }
    for (const group of groups.values()) {
      group.sort((a, b) => a.position - b.position || a.id - b.id);
    }
    return groups;
  }, [items]);

  if (tree.isLoading || !tree.data) {
    return <div className="text-text-dim text-sm">加载中…</div>;
  }

  if (!tree.data.tree) {
    return (
      <div className="border border-dashed border-border rounded-lg p-3 text-center text-text-dim text-sm">
        <div className="mb-2">还没有探索树</div>
        <button
          type="button"
          onClick={() => createTree.mutate({ spec_text: "探索多个方案分支" })}
          disabled={createTree.isPending}
          className="px-2.5 py-1 rounded bg-text text-bg text-[12px] font-medium disabled:opacity-50"
        >
          创建探索树
        </button>
      </div>
    );
  }

  const treeId = tree.data.tree.id;
  const doneCount = items.filter((i) => i.status === "done").length;
  const activeCount = items.filter((i) => i.status === "active").length;
  const roots = childrenByParent.get(null) ?? [];

  function cycleStatus(item: TaskItemDTO) {
    const next =
      item.status === "pending" ? "active" : item.status === "active" ? "done" : "pending";
    update.mutate({ id: item.id, status: next });
  }

  function submitAdd(parentId: number | null) {
    if (!newTitle.trim()) return;
    add.mutate({
      task_tree_id: treeId,
      parent_item_id: parentId,
      title: newTitle.trim(),
      summary: newSummary.trim() || null,
    });
    setNewTitle("");
    setNewSummary("");
    setAddingParentId(null);
  }

  function ownerLabel(item: TaskItemDTO) {
    if (item.owner_agent_instance_id !== null) return `agent#${item.owner_agent_instance_id}`;
    if (item.owner_human_id !== null) return `human#${item.owner_human_id}`;
    return "未分配";
  }

  function renderAddForm(parentId: number | null) {
    return (
      <div className="mt-2 rounded border border-border bg-bg p-2 flex flex-col gap-1.5">
        <input
          autoFocus
          placeholder={parentId === null ? "新方案分支" : "子分支标题"}
          value={newTitle}
          onChange={(e) => setNewTitle(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) submitAdd(parentId);
            if (e.key === "Escape") setAddingParentId(null);
          }}
          className="text-[12px] px-2 py-1 border border-border rounded bg-surface-elev"
        />
        <textarea
          placeholder="目标、假设或交付物线索"
          value={newSummary}
          onChange={(e) => setNewSummary(e.target.value)}
          className="text-[12px] px-2 py-1 border border-border rounded bg-surface-elev min-h-14 resize-none"
        />
        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={() => setAddingParentId(null)}
            className="text-[11px] text-text-dim hover:text-text"
          >
            取消
          </button>
          <button
            type="button"
            onClick={() => submitAdd(parentId)}
            disabled={!newTitle.trim() || add.isPending}
            className="px-2 py-1 rounded bg-text text-bg text-[11px] font-medium disabled:opacity-50"
          >
            添加
          </button>
        </div>
      </div>
    );
  }

  function renderBranch(item: TaskItemDTO, depth: number) {
    const children = childrenByParent.get(item.id) ?? [];
    return (
      <div key={item.id} className="relative">
        {depth > 0 && (
          <div className="absolute -left-3 top-4 h-px w-3 bg-border-soft" aria-hidden />
        )}
        <div
          className={cn(
            "rounded-md border bg-bg px-3 py-2",
            item.status === "active" && "border-status-work",
            item.status === "done" && "border-status-on/50",
            item.status === "pending" && "border-border",
          )}
        >
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <div className="font-medium text-[12.5px] truncate">{item.title}</div>
              <div className="text-[11px] text-text-dim mt-0.5">
                {ownerLabel(item)}
              </div>
            </div>
            <button
              type="button"
              onClick={() => cycleStatus(item)}
              className={cn(
                "shrink-0 rounded px-2 py-0.5 text-[10.5px] border",
                item.status === "active" && "border-status-work text-status-work",
                item.status === "done" && "border-status-on text-status-on",
                item.status === "pending" && "border-border text-text-dim",
              )}
            >
              {statusLabel[item.status]}
            </button>
          </div>
          {item.summary && (
            <div className="mt-1.5 text-[11.5px] text-text-muted leading-snug">
              {item.summary}
            </div>
          )}
          <div className="mt-2 flex flex-wrap gap-2 text-[10.5px] text-text-dim">
            {item.linked_message_id !== null && <span>消息 #{item.linked_message_id}</span>}
            {item.deliverable_artifact_id !== null && <span>交付物 #{item.deliverable_artifact_id}</span>}
            <button
              type="button"
              onClick={() => setAddingParentId(item.id)}
              className="hover:text-text"
            >
              + 子分支
            </button>
          </div>
          {addingParentId === item.id && renderAddForm(item.id)}
        </div>
        {children.length > 0 && (
          <div className="relative ml-5 mt-2 flex flex-col gap-2 border-l border-border-soft pl-3">
            {children.map((child) => renderBranch(child, depth + 1))}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="border border-border-soft rounded-lg bg-surface-elev p-3 flex flex-col gap-3">
      <div className="flex items-baseline justify-between gap-2">
        <span className="font-semibold text-[13px]">探索树</span>
        <span className="font-mono text-[11px] text-text-dim">
          {activeCount} active · {doneCount} / {items.length} done
        </span>
      </div>
      <div className="pb-1">
        <div className="flex flex-col gap-2">
          {roots.length === 0 ? (
            <div className="border border-dashed border-border rounded p-3 text-center text-text-dim text-sm">
              还没有方案分支
            </div>
          ) : (
            roots.map((root) => renderBranch(root, 0))
          )}
        </div>
      </div>
      {addingParentId === "root" ? (
        renderAddForm(null)
      ) : (
        <button
          type="button"
          onClick={() => setAddingParentId("root")}
          className="text-[11px] text-text-dim hover:text-text text-left"
        >
          + 添加方案分支
        </button>
      )}
    </div>
  );
}
