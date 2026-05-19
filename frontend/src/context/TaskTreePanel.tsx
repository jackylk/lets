import { cn } from "../lib/cn";

export interface TaskItem {
  title: string;
  owner_name?: string;
  status?: "pending" | "active" | "done";
}

interface Props { title: string; items: TaskItem[] }

export function TaskTreePanel({ title, items }: Props) {
  const done = items.filter((i) => i.status === "done").length;
  return (
    <div className="border border-border-soft rounded-lg bg-surface-elev p-3 flex flex-col gap-2">
      <div className="flex items-baseline justify-between">
        <span className="font-semibold text-[13px]">{title}</span>
        <span className="font-mono text-[11px] text-text-dim">{done} / {items.length} done</span>
      </div>
      <ul className="flex flex-col gap-1">
        {items.map((it, i) => (
          <li key={i} className="flex items-center gap-2 text-[12.5px]">
            <span
              className={cn(
                "w-2 h-2 rounded-full flex-shrink-0",
                it.status === "done" && "bg-status-on",
                it.status === "active" && "bg-status-work",
                (!it.status || it.status === "pending") && "border border-border bg-surface",
              )}
            />
            <span className={cn("flex-1 truncate", it.status === "done" && "text-text-dim line-through")}>
              {it.title}
            </span>
            {it.owner_name && (
              <span className="text-[11px] font-mono text-text-dim flex-shrink-0">{it.owner_name}</span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
