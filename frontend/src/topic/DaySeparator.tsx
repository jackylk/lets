export function DaySeparator({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-3 my-4 text-[11px] uppercase tracking-wider text-text-dim font-semibold">
      <div className="flex-1 h-px bg-border-soft" />
      <span>{label}</span>
      <div className="flex-1 h-px bg-border-soft" />
    </div>
  );
}
