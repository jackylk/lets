import { Avatar } from "../messages/Avatar";
import { formatHHMM } from "../lib/time";

interface Action { label: string; onClick: () => void }

interface Props {
  avatar: { kind: "human" | "claude" | "codex" | "system"; initial: string };
  whoLabel: string;
  timeIso: string;
  what: string;
  topicRef: { id: string; title: string };
  primary: Action;
  secondary?: Action;
}

export function AttentionCard({ avatar, whoLabel, timeIso, what, topicRef, primary, secondary }: Props) {
  return (
    <div className="grid grid-cols-[28px_1fr_auto] gap-3 items-start border border-border-soft border-l-2 border-l-accent rounded bg-surface-elev p-3 shadow-sm">
      <Avatar kind={avatar.kind} initial={avatar.initial} />
      <div className="min-w-0">
        <div className="text-[12px] text-text-muted">
          <span className="font-semibold text-text">{whoLabel}</span> · {formatHHMM(timeIso)}
        </div>
        <div className="font-[var(--font-display)] text-[15px] leading-snug mt-0.5">{what}</div>
        <div className="text-[11px] text-text-dim mt-1">
          <span className="font-mono">{topicRef.id}</span> · {topicRef.title}
        </div>
      </div>
      <div className="flex flex-col gap-1 self-center">
        <button
          type="button"
          onClick={primary.onClick}
          className="px-2 py-1 rounded-[3px] bg-text text-bg text-[12px] font-medium whitespace-nowrap"
        >
          {primary.label}
        </button>
        {secondary && (
          <button
            type="button"
            onClick={secondary.onClick}
            className="px-2 py-1 rounded-[3px] border border-border text-[12px] whitespace-nowrap"
          >
            {secondary.label}
          </button>
        )}
      </div>
    </div>
  );
}
