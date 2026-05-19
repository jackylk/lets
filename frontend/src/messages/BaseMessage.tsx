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
  finding: "bg-finding-bg/40 border-l-2 border-finding pl-3",
  decision: "bg-decision-bg/40 border-l-2 border-decision pl-3",
  handoff: "bg-handoff-bg/40 border-l-2 border-handoff pl-3",
  review: "bg-review-bg/40 border-l-2 border-review pl-3",
  artifact: "bg-artifact-bg/40 border-l-2 border-artifact pl-3",
  spec: "bg-spec-bg/40 border-l-2 border-spec pl-3",
  proactive: "bg-proactive-bg/40 border-l-2 border-proactive pl-3",
  tree: "bg-tree-bg/40 border-l-2 border-tree pl-3",
  nudge: "bg-nudge-bg border-l-2 border-nudge pl-3 italic text-nudge",
  question: "bg-accent-soft/30 border-l-2 border-accent pl-3",
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
