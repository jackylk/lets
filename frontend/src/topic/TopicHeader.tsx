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
}

export function TopicHeader({ title, goal, onOpenMenu }: TopicHeaderProps) {
  return (
    <header className="flex items-center gap-4 px-6 py-3 border-b border-border-soft min-w-0">
      <h1 className="font-[var(--font-display)] font-semibold text-lg truncate">{title}</h1>
      {goal && (
        <TopicHeaderProgress
          doneCount={goal.doneCount}
          totalCount={goal.totalCount}
          currentTaskTitle={goal.currentTaskTitle ?? null}
        />
      )}
      <div className="flex-1" />
      <button
        type="button"
        onClick={onOpenMenu}
        aria-label="topic menu"
        className="px-2 py-1 rounded hover:bg-surface-hover text-text-muted"
      >
        ⋯
      </button>
    </header>
  );
}
