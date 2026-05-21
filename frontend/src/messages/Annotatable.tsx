import { useEffect, useRef, useState, type ReactNode } from "react";
import { usePostMessage, useSessionMe } from "../api/queries";

interface Props {
  /** Topic this message belongs to — needed to post the annotation. */
  topicId: number;
  /** The message being annotated. */
  targetMessageId: number;
  children: ReactNode;
}

/**
 * Wraps an agent reply body. When the user selects any text inside, a small
 * floating button "添加批注" appears near the selection. Click → an inline
 * input. Submit posts an `annotation` typed message whose metadata carries
 * the quoted span and target message id; the StreamProvider's projection
 * later surfaces these as pins below the targeted message.
 */
export function Annotatable({ topicId, targetMessageId, children }: Props) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const [popover, setPopover] = useState<null | { x: number; y: number; quote: string }>(null);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const post = usePostMessage(topicId);
  const me = useSessionMe();

  useEffect(() => {
    function onMouseUp() {
      const sel = window.getSelection();
      const wrap = wrapRef.current;
      if (!sel || sel.isCollapsed || !wrap) {
        // selection ended outside the wrap; close any open popover unless
        // the user is already editing.
        if (!editing) setPopover(null);
        return;
      }
      // Selection has to start AND end inside our element.
      const range = sel.getRangeAt(0);
      if (!wrap.contains(range.startContainer) || !wrap.contains(range.endContainer)) {
        if (!editing) setPopover(null);
        return;
      }
      const quote = sel.toString().trim();
      if (!quote) {
        if (!editing) setPopover(null);
        return;
      }
      const rect = range.getBoundingClientRect();
      const wrapRect = wrap.getBoundingClientRect();
      setPopover({
        x: rect.right - wrapRect.left,
        y: rect.top - wrapRect.top,
        quote,
      });
    }
    document.addEventListener("mouseup", onMouseUp);
    return () => document.removeEventListener("mouseup", onMouseUp);
  }, [editing]);

  function openEditor() {
    if (!popover) return;
    setDraft("");
    setEditing(true);
  }
  function cancel() {
    setEditing(false);
    setPopover(null);
    setDraft("");
    window.getSelection()?.removeAllRanges();
  }
  async function submit() {
    if (!popover || !me.data) return;
    const body = draft.trim();
    if (!body) return;
    await post.mutateAsync({
      topic_id: topicId,
      type: "annotation",
      actor_type: "human",
      actor_id: me.data.human.id,
      body,
      metadata: {
        target_message_id: targetMessageId,
        target_quote: popover.quote.slice(0, 200),
      },
    });
    cancel();
  }

  return (
    <div ref={wrapRef} className="relative">
      {children}

      {popover && !editing && (
        <button
          type="button"
          onMouseDown={(e) => { e.preventDefault(); openEditor(); }}
          style={{ left: Math.max(0, popover.x + 6), top: Math.max(0, popover.y - 32) }}
          className="absolute z-10 px-2.5 py-1 bg-text text-bg text-[11.5px] rounded-[3px] font-medium shadow-lg whitespace-nowrap"
        >
          添加批注
        </button>
      )}

      {popover && editing && (
        <div
          style={{ left: Math.max(0, popover.x + 6), top: Math.max(0, popover.y) }}
          className="absolute z-20 w-80 max-w-[90vw] bg-bg border border-border rounded-md p-3 shadow-lg flex flex-col gap-2"
        >
          <div className="text-[11px] text-text-dim italic border-l-2 border-annotation pl-2">
            “{popover.quote.length > 80 ? popover.quote.slice(0, 80) + "…" : popover.quote}”
          </div>
          <textarea
            autoFocus
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="你的疑问 / 建议 / 反馈"
            rows={3}
            className="bg-transparent outline-none resize-none text-[13px] leading-relaxed"
          />
          <div className="flex justify-end gap-2 items-center">
            <span className="text-[10.5px] text-text-dim italic mr-auto">
              发送后，agent 下次回复时会看到这条批注
            </span>
            <button
              type="button"
              onClick={cancel}
              className="text-[12px] text-text-dim hover:text-text px-2 py-0.5"
            >取消</button>
            <button
              type="button"
              onClick={submit}
              disabled={!draft.trim() || post.isPending}
              className="text-[12px] bg-text text-bg px-3 py-0.5 rounded-[3px] disabled:opacity-40 font-medium"
            >{post.isPending ? "…" : "批注"}</button>
          </div>
        </div>
      )}
    </div>
  );
}
