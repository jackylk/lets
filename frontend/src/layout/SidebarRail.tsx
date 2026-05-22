interface Props {
  attentionCount?: number;
  onClickAttention?: () => void;
  onClickSettings?: () => void;
}

/**
 * The slim 48px-wide column shown when the sidebar is collapsed. Just keeps
 * a Let's monogram + a way back to the two pages that matter (attention,
 * settings). The 展开 toggle is rendered by AppShell itself.
 */
export function SidebarRail({ attentionCount = 0, onClickAttention, onClickSettings }: Props) {
  return (
    <div className="h-full flex flex-col items-center pt-12 gap-5 select-none bg-surface-elev/30">
      <div
        title="Let's"
        className="w-7 h-7 grid place-items-center rounded-md border border-border-soft bg-surface-elev font-[var(--font-display)] font-bold text-[18px] leading-none text-text shadow-sm"
      >
        L
      </div>
      <button
        type="button"
        title={attentionCount > 0 ? `${attentionCount} 条待处理` : "待处理"}
        onClick={onClickAttention}
        className="relative w-8 h-8 grid place-items-center rounded-md text-text-dim hover:bg-surface-hover hover:text-text"
      >
        <span className="font-mono text-[10px] uppercase tracking-[0.04em]">待处</span>
        {attentionCount > 0 && (
          <span className="absolute -top-1 -right-1 bg-accent-soft text-accent-text border border-accent-border rounded-[3px] text-[9px] font-mono px-1 leading-none py-px">
            {attentionCount}
          </span>
        )}
      </button>
      <div className="flex-1" />
      <button
        type="button"
        title="设置"
        onClick={onClickSettings}
        className="w-8 h-8 grid place-items-center rounded-md text-text-dim hover:bg-surface-hover hover:text-text mb-4"
      >
        <span className="font-mono text-[10px] uppercase tracking-[0.04em]">设置</span>
      </button>
    </div>
  );
}
