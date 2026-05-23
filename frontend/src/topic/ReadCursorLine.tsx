/**
 * Horizontal divider that sits between the last message any agent has
 * acknowledged reading and the first unread human message.
 */
export function ReadCursorLine() {
  return (
    <div className="flex items-center gap-3 my-2.5 text-[10.5px] font-mono uppercase tracking-[0.04em] text-accent-text">
      <span className="flex-1 border-t border-dashed border-accent-border" />
      <span className="grid place-items-center w-[18px] h-[18px] rounded-full border-2 border-accent text-[9px] font-bold bg-bg shadow-[0_0_0_4px_var(--color-accent-soft)]">
        ✓
      </span>
      <span className="font-semibold">Agent 已读到此处</span>
      <span className="flex-1 border-t border-dashed border-accent-border" />
    </div>
  );
}
