import { useMemo } from "react";
import type { MessageDTO } from "../api/types";
import { Avatar } from "./Avatar";
import { formatHHMM } from "../lib/time";
import { useStream } from "./StreamContext";

interface Actor { kind: "human" | "claude" | "codex" | "system"; initial: string; displayName: string }

/**
 * Single-line summary of an agent chat: a folded chat bubble. Shows the
 * agent-provided headline (≤30 chars) + structural counts derived from
 * metadata (no LLM call needed). Click anywhere → expand.
 */
export function CollapsedAgentMessage({ message, actor }: { message: MessageDTO; actor: Actor }) {
  const { byId, toggleExpanded } = useStream();

  const summary = useMemo(() => {
    const meta = (message.metadata as Record<string, unknown> | null) ?? {};
    const headline = typeof meta.headline === "string" ? meta.headline.trim() : "";
    const cites = Array.isArray(meta.cites) ? (meta.cites as number[]).length : 0;
    const mermaid = (message.body.match(/```mermaid/g) || []).length;

    // Count pane updates whose promoted_from === this.id (proactive_finding /
    // decision / question / finding with discussion_kind).
    let suggestions = 0;
    for (const m of byId.values()) {
      const mm = (m.metadata as Record<string, unknown> | null) ?? {};
      if (mm.promoted_from === message.id && typeof mm.discussion_kind === "string") {
        suggestions += 1;
      }
    }
    return {
      headline,
      cites,
      mermaid,
      suggestions,
      bodyLen: message.body.length,
    };
  }, [message, byId]);

  const nameColor =
    actor.kind === "claude" ? "text-agent-claude" :
    actor.kind === "codex" ? "text-agent-codex" : "text-text-dim";

  const bits: string[] = [];
  if (summary.suggestions > 0) bits.push(`${summary.suggestions} 个建议`);
  if (summary.mermaid > 0) bits.push(`${summary.mermaid} 张图`);
  if (summary.cites > 0) bits.push(`基于 ${summary.cites} 条`);
  if (bits.length === 0) bits.push(`${summary.bodyLen} 字`);

  return (
    <div
      data-testid="message-row"
      data-msg-id={message.id}
      data-collapsed
      role="button"
      tabIndex={0}
      onClick={() => toggleExpanded(message.id)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          toggleExpanded(message.id);
        }
      }}
      className="grid grid-cols-[28px_1fr_auto] gap-3 py-1.5 px-1 -mx-1 rounded items-center cursor-pointer hover:bg-surface-elev/60 transition-colors"
    >
      <Avatar initial={actor.initial} kind={actor.kind} />
      <div className="min-w-0 flex items-baseline gap-2 flex-wrap text-[13px]">
        <span className={`font-semibold ${nameColor}`}>{actor.displayName}</span>
        <span className="text-text-dim text-[11px] font-mono">{formatHHMM(message.created_at)}</span>
        {summary.headline && (
          <span className="text-text truncate max-w-[42ch]" title={summary.headline}>
            {summary.headline}
          </span>
        )}
        <span className="text-text-dim text-[11.5px]">·</span>
        <span className="text-text-dim text-[11.5px] font-mono">
          {bits.join(" · ")}
        </span>
      </div>
      <span className="text-[11px] text-accent-text font-mono uppercase tracking-[0.04em] pr-1">
        展开
      </span>
    </div>
  );
}
