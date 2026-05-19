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
        "rounded-full grid place-items-center font-semibold leading-none flex-shrink-0",
        size === "md" ? "w-7 h-7 text-[12px]" : "w-5 h-5 text-[10px]",
        kind === "human" && "bg-human-bg text-human",
        kind === "claude" && "bg-agent-claude-bg text-agent-claude",
        kind === "codex" && "bg-agent-codex-bg text-agent-codex",
        kind === "system" && "bg-surface-hover text-text-dim",
      )}
    >
      {initial}
    </div>
  );
}
