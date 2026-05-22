import { cn } from "../lib/cn";

export type MobileTab = "topic" | "attention" | "context";

interface Props {
  active: MobileTab;
  onSelect: (tab: MobileTab) => void;
}

const TABS: Array<{ key: MobileTab; label: string }> = [
  { key: "topic", label: "Topic" },
  { key: "attention", label: "Attention" },
  { key: "context", label: "Context" },
];

export function BottomTabs({ active, onSelect }: Props) {
  return (
    <nav className="md:hidden fixed bottom-0 inset-x-0 h-14 bg-surface-elev border-t border-border-soft flex">
      {TABS.map((t) => (
        <button
          key={t.key}
          type="button"
          onClick={() => onSelect(t.key)}
          className={cn(
            "flex-1 flex flex-col items-center justify-center gap-0.5 text-[11px]",
            active === t.key ? "text-text font-semibold" : "text-text-dim",
          )}
        >
          <span>{t.label}</span>
        </button>
      ))}
    </nav>
  );
}
