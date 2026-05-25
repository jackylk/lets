import { cn } from "../lib/cn";

export type MobileTab = "workspace" | "topic";

interface Props {
  active: MobileTab;
  onSelect: (tab: MobileTab) => void;
}

const TABS: Array<{ key: MobileTab; label: string }> = [
  { key: "workspace", label: "工作区" },
  { key: "topic", label: "话题" },
];

export function BottomTabs({ active, onSelect }: Props) {
  return (
    <nav className="md:hidden fixed bottom-0 inset-x-0 z-30 h-[calc(56px+env(safe-area-inset-bottom))] bg-surface-elev border-t border-border-soft flex pb-[env(safe-area-inset-bottom)]">
      {TABS.map((t) => (
        <button
          key={t.key}
          type="button"
          onClick={() => onSelect(t.key)}
          className={cn(
            "flex-1 min-w-0 flex flex-col items-center justify-center gap-0.5 text-[11px]",
            active === t.key ? "text-text font-semibold" : "text-text-dim",
          )}
        >
          <span className="truncate">{t.label}</span>
        </button>
      ))}
    </nav>
  );
}
