interface Props {
  doneCount: number;
  totalCount: number;
  currentTaskTitle?: string | null;
}

export function TopicHeaderProgress({ doneCount, totalCount, currentTaskTitle }: Props) {
  const pct = totalCount === 0 ? 0 : Math.round((doneCount / totalCount) * 100);
  const stroke = 2;
  const r = 7;
  const c = 2 * Math.PI * r;
  const dash = (pct / 100) * c;
  return (
    <div className="flex items-center gap-2 text-[12px] text-text-muted">
      <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden>
        <circle cx="9" cy="9" r={r} fill="none" stroke="var(--color-border)" strokeWidth={stroke} />
        <circle
          cx="9" cy="9" r={r} fill="none"
          stroke="var(--color-accent)" strokeWidth={stroke}
          strokeDasharray={`${dash} ${c}`} strokeLinecap="round"
          transform="rotate(-90 9 9)"
        />
      </svg>
      <span className="font-mono text-text">{pct}%</span>
      <span className="font-mono">{doneCount}/{totalCount}</span>
      {currentTaskTitle && (
        <>
          <span className="text-text-dim">→</span>
          <span className="truncate max-w-[16ch]" title={currentTaskTitle}>{currentTaskTitle}</span>
        </>
      )}
    </div>
  );
}
