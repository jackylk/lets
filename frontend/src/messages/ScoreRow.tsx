import { useMemo } from "react";
import { useStream } from "./StreamContext";
import { usePostMessage, useSessionMe } from "../api/queries";

/**
 * Two tiny vote buttons under each agent reply: +1 / -1. Each click posts
 * an annotation with metadata.score = ±1 targeting this message. Scores
 * aggregate across all humans in the topic and downstream `lets spec` can
 * use them to filter / weight items when assembling the handoff doc.
 *
 * Clicking again removes the user's previous vote (re-post with score=0)
 * so the affordance is reversible. We deliberately don't try to be clever
 * about "you already voted +1, ignore" — re-posting score=0 is simple and
 * correct; the latest vote per (user, target) wins.
 */
export function ScoreRow({
  topicId,
  messageId,
}: {
  topicId: number;
  messageId: number;
}) {
  const { byId } = useStream();
  const post = usePostMessage(topicId);
  const me = useSessionMe();

  const { total, myVote } = useMemo(() => {
    // Latest score per (actor_id) — re-votes overwrite earlier ones.
    const latestByActor = new Map<number, number>();
    for (const m of byId.values()) {
      if (m.type !== "annotation") continue;
      const meta = m.metadata as Record<string, unknown> | null;
      if (!meta) continue;
      if (meta.target_message_id !== messageId) continue;
      if (typeof meta.score !== "number") continue;
      const aid = m.actor_id;
      if (aid == null) continue;
      latestByActor.set(aid, meta.score);
    }
    let sum = 0;
    for (const v of latestByActor.values()) sum += v;
    const mine = me.data ? latestByActor.get(me.data.human.id) ?? 0 : 0;
    return { total: sum, myVote: mine };
  }, [byId, messageId, me.data]);

  async function vote(direction: 1 | -1) {
    if (!me.data) return;
    // Toggle: if the user is already at this direction, set to 0; else set.
    const next = myVote === direction ? 0 : direction;
    await post.mutateAsync({
      topic_id: topicId,
      type: "annotation",
      actor_type: "human",
      actor_id: me.data.human.id,
      body: "",
      metadata: {
        target_message_id: messageId,
        score: next,
      },
    });
  }

  const upActive = myVote === 1;
  const downActive = myVote === -1;

  return (
    <div className="mt-1.5 flex items-center gap-2 text-[10.5px] font-mono uppercase tracking-[0.04em]">
      <button
        type="button"
        onClick={() => vote(1)}
        title={upActive ? "取消 +1" : "标记为有价值 +1（spec 会优先收录）"}
        className={
          "px-1.5 py-px rounded border " +
          (upActive
            ? "text-status-on border-status-on bg-finding-bg"
            : "text-text-dim border-border-soft hover:text-status-on hover:border-status-on")
        }
      >
        +1
      </button>
      <button
        type="button"
        onClick={() => vote(-1)}
        title={downActive ? "取消 -1" : "标记为不靠谱 -1（spec 会过滤）"}
        className={
          "px-1.5 py-px rounded border " +
          (downActive
            ? "text-accent-text border-accent-border bg-accent-soft"
            : "text-text-dim border-border-soft hover:text-accent-text hover:border-accent-border")
        }
      >
        −1
      </button>
      {total !== 0 && (
        <span
          className={
            total > 0 ? "text-status-on" : "text-accent-text"
          }
          title={`累计评分 ${total > 0 ? "+" : ""}${total}`}
        >
          {total > 0 ? `+${total}` : total}
        </span>
      )}
    </div>
  );
}
