import { useState } from "react";
import { usePostMessage, useSessionMe } from "../api/queries";

interface Props {
  /** Topic id (where to post the resolving decision). */
  topicId: number;
  /** The question message being resolved. */
  questionId: number;
  /** Question body, used as placeholder context. */
  questionBody: string;
  /** Called after a successful post — caller may close the inline editor. */
  onDone: () => void;
}

/**
 * Inline answer editor for an open_question card. Submitting posts a
 * `decision` typed message with metadata.resolves_question pointing back
 * to this question. The right-pane projection moves the question OFF
 * 「待回答」and into 「共识」(meeting record style).
 */
export function ResolveQuestionInline({ topicId, questionId, questionBody, onDone }: Props) {
  const [draft, setDraft] = useState("");
  const post = usePostMessage(topicId);
  const me = useSessionMe();

  async function submit() {
    const body = draft.trim();
    if (!body || !me.data) return;
    await post.mutateAsync({
      topic_id: topicId,
      type: "decision",
      actor_type: "human",
      actor_id: me.data.human.id,
      body,
      metadata: {
        discussion_kind: "decision",
        resolves_question: questionId,
        promoted_from: questionId,
      },
    });
    setDraft("");
    onDone();
  }

  return (
    <div className="mt-1 border border-border-soft rounded bg-bg p-2 flex flex-col gap-1.5">
      <div className="text-[10.5px] text-text-dim italic line-clamp-2">
        {questionBody}
      </div>
      <textarea
        autoFocus
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        placeholder="一句话回答 / 决定…"
        rows={2}
        onKeyDown={(e) => {
          if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
            e.preventDefault();
            submit();
          } else if (e.key === "Escape") {
            onDone();
          }
        }}
        className="bg-transparent outline-none resize-none text-[12.5px] leading-relaxed"
      />
      <div className="flex items-center gap-2 justify-end">
        <button
          type="button"
          onClick={onDone}
          className="text-[11px] text-text-dim hover:text-text px-1.5 py-px"
        >取消</button>
        <button
          type="button"
          onClick={submit}
          disabled={!draft.trim() || post.isPending}
          className="text-[11px] bg-text text-bg px-2 py-px rounded-[3px] disabled:opacity-40 font-medium"
        >{post.isPending ? "…" : "记为共识"}</button>
      </div>
    </div>
  );
}
