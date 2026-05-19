import type { MessageDTO, TaskTreeProposalMeta } from "../api/types";
import { BaseMessage } from "./BaseMessage";
import { cn } from "../lib/cn";

interface Actor { kind: "human" | "claude" | "codex" | "system"; initial: string; displayName: string }

export function TaskTreeProposalMessage({ message, actor }: { message: MessageDTO; actor: Actor }) {
  const meta = message.metadata as Partial<TaskTreeProposalMeta>;
  const items = meta.items ?? [];
  const doneCount = items.filter((i) => i.status === "done").length;

  return (
    <BaseMessage
      actor={actor}
      timeIso={message.created_at}
      tag="task_tree"
      tone="tree"
      body={
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center gap-2 text-[13px]">
            <span className="font-semibold">{meta.title ?? "task tree"}</span>
            <span className="font-mono text-text-dim text-[11px]">{doneCount} / {items.length} done</span>
          </div>
          <ul className="flex flex-col gap-1">
            {items.map((it, i) => (
              <li key={i} className="flex items-center gap-2 text-[12.5px]">
                <span
                  className={cn(
                    "w-2 h-2 rounded-full",
                    it.status === "done" && "bg-status-on",
                    it.status === "active" && "bg-status-work",
                    (!it.status || it.status === "pending") && "border border-border bg-surface",
                  )}
                />
                <span className={it.status === "done" ? "text-text-dim line-through" : ""}>{it.title}</span>
                {it.owner_name && <span className="ml-auto text-[11px] font-mono text-text-dim">{it.owner_name}</span>}
              </li>
            ))}
          </ul>
        </div>
      }
    />
  );
}
