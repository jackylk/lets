import { useMemo, useState } from "react";
import { useStream } from "./StreamContext";
import { usePostMessage, useSessionMe } from "../api/queries";

interface NodeAnnotation {
  id: number;
  node: string;
  body: string;
  actorId: number | null;
  actorType: "human" | "agent" | "system";
  createdAt: string;
  score: number | null;
}

export function useNodeAnnotations(
  topicId: number,
  diagramMsgId: number,
): {
  byNode: Map<string, NodeAnnotation[]>;
  scoreByNode: Map<string, number>;
} {
  const { byId } = useStream();
  return useMemo(() => {
    const byNode = new Map<string, NodeAnnotation[]>();
    // Latest score per (actor, node) wins, like the message-level ScoreRow.
    const latestVote = new Map<string, number>();
    for (const m of byId.values()) {
      if (m.topic_id !== topicId) continue;
      if (m.type !== "annotation") continue;
      const meta = m.metadata as Record<string, unknown> | null;
      if (!meta) continue;
      if (meta.target_message_id !== diagramMsgId) continue;
      const node = typeof meta.target_quote === "string" ? meta.target_quote : null;
      if (!node) continue;
      const score = typeof meta.score === "number" ? meta.score : null;
      const item: NodeAnnotation = {
        id: m.id,
        node,
        body: m.body,
        actorId: m.actor_id,
        actorType: m.actor_type,
        createdAt: m.created_at,
        score,
      };
      // Voting messages (score!=null) don't go in the comment list.
      if (score === null) {
        const arr = byNode.get(node) ?? [];
        arr.push(item);
        byNode.set(node, arr);
      } else if (item.actorId != null) {
        latestVote.set(`${item.actorId}:${node}`, score);
      }
    }
    const scoreByNode = new Map<string, number>();
    for (const [k, v] of latestVote) {
      const node = k.split(":").slice(1).join(":");
      scoreByNode.set(node, (scoreByNode.get(node) ?? 0) + v);
    }
    // Sort comments within each node by id asc (oldest first).
    for (const arr of byNode.values()) arr.sort((a, b) => a.id - b.id);
    return { byNode, scoreByNode };
  }, [byId, topicId, diagramMsgId]);
}

/**
 * Selected-node feedback editor used inside DiagramOverlay. Shows the
 * selected node's text, current vote/annotation state, and lets the
 * human vote or comment. Posts annotations whose
 * `metadata.target_message_id` points at the diagram source message and
 * `metadata.target_quote` carries the node text. `lets spec` and the
 * right-pane projections both already know how to read this shape.
 */
export function NodeFeedbackPanel({
  topicId,
  diagramMsgId,
  selectedNode,
}: {
  topicId: number;
  diagramMsgId: number;
  selectedNode: string | null;
}) {
  const { byNode, scoreByNode } = useNodeAnnotations(topicId, diagramMsgId);
  const post = usePostMessage(topicId);
  const me = useSessionMe();
  const [draft, setDraft] = useState("");

  // Per-user latest vote on this node (for toggle UX).
  const myVote = useMemo(() => {
    if (!selectedNode || !me.data) return 0;
    return Number(localStorage.getItem(_voteKey(diagramMsgId, selectedNode, me.data.human.id))) || 0;
  }, [selectedNode, diagramMsgId, me.data, scoreByNode]);

  if (!selectedNode) {
    return (
      <div className="text-[12px] text-text-dim italic py-2 px-1">
        点图里任意节点 — 可以给它 +1/-1 或加一条文字批注。
      </div>
    );
  }

  const comments = byNode.get(selectedNode) ?? [];
  const score = scoreByNode.get(selectedNode) ?? 0;

  async function vote(direction: 1 | -1) {
    if (!me.data) return;
    const key = _voteKey(diagramMsgId, selectedNode!, me.data.human.id);
    const prev = Number(localStorage.getItem(key)) || 0;
    const next = prev === direction ? 0 : direction;
    localStorage.setItem(key, String(next));
    await post.mutateAsync({
      topic_id: topicId,
      type: "annotation",
      actor_type: "human",
      actor_id: me.data.human.id,
      body: "",
      metadata: {
        target_message_id: diagramMsgId,
        target_quote: selectedNode,
        score: next,
      },
    });
  }

  async function comment() {
    const body = draft.trim();
    if (!body || !me.data) return;
    await post.mutateAsync({
      topic_id: topicId,
      type: "annotation",
      actor_type: "human",
      actor_id: me.data.human.id,
      body,
      metadata: {
        target_message_id: diagramMsgId,
        target_quote: selectedNode,
      },
    });
    setDraft("");
  }

  return (
    <div className="border border-border-soft rounded bg-surface-elev p-3 flex flex-col gap-2.5 text-[13px]">
      <div className="flex items-baseline gap-2">
        <span className="font-mono text-[10px] uppercase tracking-[0.04em] text-text-dim shrink-0">
          节点
        </span>
        <span className="font-semibold leading-snug">{selectedNode}</span>
      </div>

      <div className="flex items-center gap-2 text-[11px] font-mono uppercase tracking-[0.04em]">
        <button
          type="button"
          onClick={() => vote(1)}
          className={
            "px-1.5 py-px rounded border " +
            (myVote === 1
              ? "text-status-on border-status-on bg-finding-bg"
              : "text-text-dim border-border-soft hover:text-status-on hover:border-status-on")
          }
        >
          +1
        </button>
        <button
          type="button"
          onClick={() => vote(-1)}
          className={
            "px-1.5 py-px rounded border " +
            (myVote === -1
              ? "text-accent-text border-accent-border bg-accent-soft"
              : "text-text-dim border-border-soft hover:text-accent-text hover:border-accent-border")
          }
        >
          −1
        </button>
        {score !== 0 && (
          <span
            className={score > 0 ? "text-status-on" : "text-accent-text"}
            title={`累计评分 ${score > 0 ? "+" : ""}${score}`}
          >
            {score > 0 ? `+${score}` : score}
          </span>
        )}
      </div>

      <div className="flex items-end gap-2">
        <textarea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="给这个节点加一条文字批注…"
          rows={2}
          onKeyDown={(e) => {
            if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
              e.preventDefault();
              comment();
            }
          }}
          className="flex-1 bg-transparent outline-none resize-none border border-border-soft rounded p-1.5 text-[12.5px] leading-relaxed"
        />
        <button
          type="button"
          onClick={comment}
          disabled={!draft.trim() || post.isPending}
          className="text-[11px] bg-text text-bg px-2 py-1 rounded-[3px] disabled:opacity-40 font-medium shrink-0"
        >
          批注
        </button>
      </div>

      {comments.length > 0 && (
        <div className="flex flex-col gap-1.5 mt-1">
          {comments.map((c) => (
            <div
              key={c.id}
              className="text-[12px] border-l-[2.5px] border-annotation bg-annotation-bg/60 pl-2 pr-2 py-1 rounded-r"
            >
              <div className="text-[10px] font-mono text-text-dim uppercase tracking-[0.04em]">
                批注 · {c.actorType === "human" ? "human" : "agent"}
              </div>
              <div className="text-text leading-relaxed">{c.body}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function _voteKey(diagramMsgId: number, node: string, humanId: number): string {
  return `lets:node-vote:${diagramMsgId}:${humanId}:${node}`;
}
