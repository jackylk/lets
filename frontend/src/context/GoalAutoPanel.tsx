import { useMemo } from "react";
import { useTopicMessages } from "../api/queries";

interface Props {
  topicId: number;
}

/**
 * Goal panel that auto-derives the topic's goal from the conversation
 * when nobody has formally posted a goal_proposal yet:
 *
 *   1. If any `goal_proposal` exists → render its body (most recent wins).
 *   2. Else, if the topic has any human `chat` → treat the first one as
 *      the implicit goal and surface it as "未确认 · 来自首条对话".
 *   3. Else → "尚未设定目标".
 */
export function GoalAutoPanel({ topicId }: Props) {
  const messages = useTopicMessages(topicId);
  const msgs = messages.data?.messages ?? [];

  const formalGoal = useMemo(() => {
    const proposals = msgs.filter((m) => m.type === "goal_proposal");
    return proposals[proposals.length - 1] ?? null;
  }, [msgs]);

  const implicitGoal = useMemo(() => {
    if (formalGoal) return null;
    return (
      msgs.find((m) => m.type === "chat" && m.actor_type === "human") ?? null
    );
  }, [msgs, formalGoal]);

  if (messages.isLoading) {
    return <div className="text-text-dim text-sm">…</div>;
  }

  if (!formalGoal && !implicitGoal) {
    return (
      <div className="border border-dashed border-border rounded p-3 text-center text-text-dim text-sm">
        尚未设定目标
      </div>
    );
  }

  const goal = (formalGoal ?? implicitGoal)!;
  const isImplicit = !formalGoal;

  return (
    <div className="border border-border-soft rounded-lg bg-surface-elev p-3 flex flex-col gap-2">
      <div className="flex items-center gap-2">
        <span className="text-[11px] uppercase tracking-wider text-text-dim font-semibold">
          {isImplicit ? "对话推断" : "已确认目标"}
        </span>
        {isImplicit && (
          <span className="ml-auto text-[10px] font-mono px-1.5 py-px rounded bg-surface text-text-muted">
            来自首条对话
          </span>
        )}
        {!isImplicit && (
          <span className="ml-auto text-[10px] font-mono px-1.5 py-px rounded bg-accent-soft text-accent-text">
            goal_proposal #{goal.id}
          </span>
        )}
      </div>
      <p className="text-[13px] text-text leading-relaxed whitespace-pre-wrap">
        {goal.body}
      </p>
      {isImplicit && (
        <div className="text-[11px] text-text-dim italic">
          团队可发 <span className="font-mono">goal_proposal</span> 消息正式确认目标。
        </div>
      )}
    </div>
  );
}
