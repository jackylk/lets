interface Item { path: string; version: string; pending: boolean }
export function SpecTouchedPanel({ items }: { items: Item[] }) {
  return (
    <div className="flex flex-col gap-1">
      {items.map((it) => (
        <div key={it.path} className="flex items-center gap-2 text-[12px] font-mono">
          <span className="text-text-dim">⟐</span>
          <span className="truncate flex-1">{it.path}</span>
          <span className={it.pending ? "text-spec" : "text-text-dim"}>{it.version}</span>
        </div>
      ))}
    </div>
  );
}
