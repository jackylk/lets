import type { ReactNode } from "react";
import { Avatar } from "./Avatar";
import { formatHHMM } from "../lib/time";
import { cn } from "../lib/cn";
import { useStream } from "./StreamContext";

interface ActorInfo {
  kind: "human" | "claude" | "codex" | "system";
  initial: string;
  displayName: string;
}

interface Props {
  /** Message id — required for cited-highlight to find this row. */
  msgId?: number;
  actor: ActorInfo;
  timeIso: string;
  body: ReactNode;
  tag?: string;
  tone?: "default" | "status" | "finding" | "decision" | "handoff" | "review" |
        "artifact" | "spec" | "proactive" | "tree" | "nudge" | "question";
}

const SHELL = "bg-surface-elev border border-border-soft shadow-sm";

const toneClasses: Record<NonNullable<Props["tone"]>, string> = {
  default: "",
  status: `${SHELL} italic`,
  finding: SHELL,
  decision: SHELL,
  handoff: SHELL,
  review: SHELL,
  artifact: SHELL,
  spec: SHELL,
  proactive: SHELL,
  tree: SHELL,
  nudge: "bg-nudge-bg border border-dashed border-border text-nudge",
  question: SHELL,
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

export function BaseMessage({ msgId, actor, timeIso, body, tag, tone = "default" }: Props) {
  const { highlighted, readCursor } = useStream();
  const isCited = msgId !== undefined && highlighted.has(msgId);
  // Mark as "unread by the agent" only for non-self posts that arrived
  // after the agent's last read cursor. Agent posts themselves are obviously
  // already known to the agent.
  const isUnread =
    msgId !== undefined &&
    readCursor > 0 &&
    msgId > readCursor &&
    actor.kind === "human";

  const nameColor =
    actor.kind === "human" ? "text-human" :
    actor.kind === "claude" ? "text-agent-claude" :
    actor.kind === "codex" ? "text-agent-codex" : "text-text-dim";

  return (
    <div
      data-testid="message-row"
      data-msg-id={msgId}
      data-unread={isUnread || undefined}
      className={cn(
        "grid grid-cols-[28px_1fr] gap-3 py-3 transition-colors rounded",
        isCited && "bg-accent-soft/60 shadow-[inset_2px_0_0_var(--color-accent)] px-1 -mx-1",
        isUnread && "border-l-2 border-dashed border-border pl-2 -ml-2",
      )}
    >
      <Avatar initial={actor.initial} kind={actor.kind} />
      <div className="min-w-0">
        <div className="flex items-baseline gap-2 flex-wrap">
          <span className={cn("font-semibold text-[14px]", nameColor)}>{actor.displayName}</span>
          <span className="text-text-dim text-[11px] font-mono">{formatHHMM(timeIso)}</span>
          {tag && (
            <span className={cn("px-1.5 py-px rounded-[3px] border border-border-soft text-[10.5px] font-mono uppercase tracking-[0.08em]", tagToneClass[tone])}>
              {tag}
            </span>
          )}
          {isUnread && (
            <span className="px-1.5 py-px rounded-[3px] border border-accent-border bg-accent-soft text-accent-text text-[9.5px] font-mono italic">
              未读
            </span>
          )}
        </div>
        <div className={cn("text-[14.5px] leading-[1.72] py-1 px-3 rounded mt-px", toneClasses[tone])}>
          {body}
        </div>
      </div>
    </div>
  );
}
