import type { ReactNode } from "react";
import { Avatar } from "./Avatar";
import { formatHHMM } from "../lib/time";
import { cn } from "../lib/cn";

interface ActorInfo {
  kind: "human" | "claude" | "codex" | "system";
  initial: string;
  displayName: string;
}

interface Props {
  actor: ActorInfo;
  timeIso: string;
  body: ReactNode;
  tag?: string;
  tone?: "default" | "status" | "finding" | "decision" | "handoff" | "review" |
        "artifact" | "spec" | "proactive" | "tree" | "nudge" | "question";
}

const toneClasses: Record<NonNullable<Props["tone"]>, string> = {
  default: "",
  status: "bg-surface-elev border border-border-soft",
  finding: "bg-finding-bg/25",
  decision: "bg-decision-bg/25",
  handoff: "bg-handoff-bg/25",
  review: "bg-review-bg/25",
  artifact: "bg-artifact-bg/25",
  spec: "bg-spec-bg/25",
  proactive: "bg-proactive-bg/25",
  tree: "bg-tree-bg/25",
  nudge: "bg-nudge-bg/60 italic text-nudge",
  question: "bg-accent-soft/20",
};

const tagToneClass: Record<NonNullable<Props["tone"]>, string> = {
  default: "",
  status: "text-status-work",
  finding: "text-finding",
  decision: "text-decision",
  handoff: "text-handoff",
  review: "text-review",
  artifact: "text-artifact",
  spec: "text-spec",
  proactive: "text-proactive",
  tree: "text-tree",
  nudge: "text-nudge",
  question: "text-accent-text",
};

export function BaseMessage({ actor, timeIso, body, tag, tone = "default" }: Props) {
  const nameColor =
    actor.kind === "human" ? "text-human" :
    actor.kind === "claude" ? "text-agent-claude" :
    actor.kind === "codex" ? "text-agent-codex" : "text-text-dim";

  return (
    <div data-testid="message-row" className="grid grid-cols-[28px_1fr] gap-3 py-2">
      <Avatar initial={actor.initial} kind={actor.kind} />
      <div className="min-w-0">
        <div className="flex items-baseline gap-2 flex-wrap">
          <span className={cn("font-semibold text-[13.5px]", nameColor)}>{actor.displayName}</span>
          <span className="text-text-dim text-[11px] font-mono">{formatHHMM(timeIso)}</span>
          {tag && (
            <span className={cn("px-1.5 py-px rounded text-[10.5px] font-mono", tagToneClass[tone])}>
              {tag}
            </span>
          )}
        </div>
        <div className={cn("text-[14px] leading-relaxed py-1 px-3 rounded mt-px", toneClasses[tone])}>
          {body}
        </div>
      </div>
    </div>
  );
}
