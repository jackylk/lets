import { cn } from "../lib/cn";

interface Props {
  initial: string;
  kind: "human" | "claude" | "codex" | "system";
  size?: "sm" | "md";
}

export function Avatar({ initial, kind, size = "md" }: Props) {
  return (
    <div
      className={cn(
        "rounded-md grid place-items-center font-semibold leading-none flex-shrink-0 border bg-surface-elev font-[var(--font-display)] shadow-[0_1px_2px_rgba(31,39,37,0.04)]",
        size === "md" ? "w-7 h-7 text-[12px]" : "w-5 h-5 text-[10px]",
        kind === "human" && "border-human text-human",
        kind === "claude" && "border-agent-claude text-agent-claude",
        kind === "codex" && "border-agent-codex text-agent-codex",
        kind === "system" && "border-border text-text-dim",
      )}
    >
      {initial}
    </div>
  );
}
