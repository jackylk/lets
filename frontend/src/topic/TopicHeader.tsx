import type { ReactNode } from "react";
import { TopicHeaderProgress } from "./TopicHeaderProgress";

interface GoalInfo {
  doneCount: number;
  totalCount: number;
  currentTaskTitle?: string | null;
}

interface TopicHeaderProps {
  title: string;
  goal?: GoalInfo;
  onOpenMenu?: () => void;
  /** Extra controls rendered on the right, before the menu button. */
  headerRight?: ReactNode;
}

export function TopicHeader({ title, goal, onOpenMenu, headerRight }: TopicHeaderProps) {
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
      <div className="hidden sm:flex items-center gap-2">{headerRight}</div>
      <button
        type="button"
        onClick={onOpenMenu}
        aria-label="topic menu"
        className="px-2 py-1 rounded-[3px] hover:bg-surface-hover text-text-muted"
      >
        ⋯
      </button>
    </header>
  );
}
