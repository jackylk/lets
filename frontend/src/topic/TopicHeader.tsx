import { useEffect, useRef, useState, type ReactNode } from "react";
import { TopicHeaderProgress } from "./TopicHeaderProgress";

interface GoalInfo {
  doneCount: number;
  totalCount: number;
  currentTaskTitle?: string | null;
}

interface TopicHeaderProps {
  title: string;
  goal?: GoalInfo;
  /** Extra controls rendered on the right, before the menu button. */
  headerRight?: ReactNode;
  mobileHeaderRight?: ReactNode;
  menu?: ReactNode;
}

export function TopicHeader({ title, goal, headerRight, mobileHeaderRight, menu }: TopicHeaderProps) {
  const menuRef = useRef<HTMLDivElement>(null);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    if (!menuOpen) return;
    function onPointerDown(event: MouseEvent) {
      if (!menuRef.current?.contains(event.target as Node)) setMenuOpen(false);
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setMenuOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [menuOpen]);

  return (
    <header className="flex items-center gap-2 md:gap-4 px-3 md:px-6 py-2.5 md:py-3 border-b border-border-soft bg-bg min-w-0">
      <h1 className="font-[var(--font-display)] font-semibold text-[16px] md:text-[18px] truncate">{title}</h1>
      {goal && (
        <TopicHeaderProgress
          doneCount={goal.doneCount}
          totalCount={goal.totalCount}
          currentTaskTitle={goal.currentTaskTitle ?? null}
        />
      )}
      <div className="flex-1" />
      {mobileHeaderRight && <div className="sm:hidden flex items-center gap-1">{mobileHeaderRight}</div>}
      <div className="hidden sm:flex items-center gap-2">{headerRight}</div>
      {menu && (
        <div ref={menuRef} className="relative">
          <button
            type="button"
            aria-label="话题菜单"
            title="话题菜单"
            onClick={() => setMenuOpen((v) => !v)}
            className="grid h-8 w-8 place-items-center rounded-[3px] text-[14px] leading-none text-text-muted hover:bg-surface-hover hover:text-text"
          >
            ...
          </button>
          {menuOpen && (
            <div className="absolute right-0 top-9 z-40 w-72 max-w-[calc(100vw-24px)] rounded-md border border-border bg-surface-elev p-2 shadow-[0_14px_40px_rgba(44,42,38,0.16)]">
              {menu}
            </div>
          )}
        </div>
      )}
    </header>
  );
}
