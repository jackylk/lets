interface Props {
  topicSlug: string;
  title: string;
  description: string;
  chips: string[];
}

export function TopicInfoCard({ topicSlug, title, description, chips }: Props) {
  return (
    <div className="border border-border-soft rounded bg-surface-elev p-3 shadow-sm">
      <div className="flex items-baseline gap-2 mb-1">
        <span className="font-mono text-[11px] text-text-dim">{topicSlug}</span>
        <span className="font-[var(--font-display)] font-semibold text-[15px] truncate">{title}</span>
      </div>
      <p className="text-[12px] text-text-muted leading-relaxed">{description}</p>
      <div className="flex flex-wrap gap-1 mt-2">
        {chips.map((c) => (
          <span key={c} className="text-[10.5px] font-mono px-1.5 py-px rounded-[3px] border border-border-soft bg-surface text-text-muted">
            {c}
          </span>
        ))}
      </div>
    </div>
  );
}
