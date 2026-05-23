import { useMemo } from "react";
import { useTopicMessages } from "../api/queries";
import { summarizeTopicGoal } from "../topic/intentSummary";

interface Props {
  topicId: number;
}

export function GoalAutoPanel({ topicId }: Props) {
  const messages = useTopicMessages(topicId);
  const msgs = messages.data?.messages ?? [];

  const formalGoal = useMemo(() => {
    const proposals = msgs.filter((m) => m.type === "goal_proposal");
    return proposals[proposals.length - 1] ?? null;
  }, [msgs]);

  const inferredIntent = useMemo(() => {
    if (formalGoal) return null;
    const first = msgs.find((m) => m.actor_type === "human" && m.type === "chat");
    return first ? summarizeTopicGoal(first.body) : null;
  }, [msgs, formalGoal]);

  if (messages.isLoading) {
    return <div className="text-text-dim text-sm">…</div>;
  }

  if (formalGoal) {
    return (
      <div className="border border-border-soft rounded bg-surface-elev p-3 flex flex-col gap-2 shadow-sm">
        <div className="flex items-center gap-2">
          <span className="text-[11px] uppercase tracking-wider text-text-dim font-semibold">
            已确认目标
          </span>
        </div>
        <p className="text-[13px] text-text leading-relaxed whitespace-pre-wrap">
          {formalGoal.body}
        </p>
      </div>
    );
  }

  if (inferredIntent) {
    return (
      <div className="border border-border-soft rounded bg-surface-elev p-3 flex flex-col gap-2 shadow-sm">
        <div className="flex items-center gap-2">
          <span className="text-[11px] uppercase tracking-wider text-text-dim font-semibold">
            意图（自动识别）
          </span>
          <span className="ml-auto text-[10px] text-text-dim italic">自动总结</span>
        </div>
        <p className="text-[13px] text-text leading-relaxed">{inferredIntent}</p>
      </div>
    );
  }

  return (
    <div className="border border-dashed border-border rounded p-3 text-center text-text-dim text-sm">
      发一条消息，目标会自动出现在这里
    </div>
  );
}
