import { useStream, type ViewMode } from "../messages/StreamContext";

const MODES: Array<{ id: ViewMode; label: string; hint: string }> = [
  { id: "full",         label: "全部",   hint: "完整显示 agent 回复" },
  { id: "collapsed",    label: "折叠",   hint: "agent 回复折成一行，点击展开" },
  { id: "humans-only",  label: "只看人", hint: "隐藏 agent，留计数标记" },
];

/**
 * Compact three-state segmented control. Lives in TopicHeader so it stays out
 * of the chat area where the user is watching the agent's state. Default = 折叠.
 */
export function ViewModeToggle() {
  const { viewMode, setViewMode } = useStream();
  return (
    <div
      role="radiogroup"
      aria-label="agent 显示模式"
      className="inline-flex items-center text-[10.5px] font-mono uppercase tracking-[0.04em] border border-border-soft rounded-[3px] overflow-hidden"
    >
      {MODES.map((m) => {
        const active = m.id === viewMode;
        return (
          <button
            key={m.id}
            type="button"
            role="radio"
            aria-checked={active}
            title={m.hint}
            onClick={() => setViewMode(m.id)}
            className={[
              "px-2 py-[2px] transition-colors border-r border-border-soft last:border-r-0",
              active
                ? "bg-text text-bg"
                : "bg-bg text-text-dim hover:text-text hover:bg-surface-elev",
            ].join(" ")}
          >
            {m.label}
          </button>
        );
      })}
    </div>
  );
}
