import { useState } from "react";
import { usePostMessage } from "../api/queries";
import { useSessionMe } from "../api/queries";

type Kind = "decision" | "option" | "open_question" | "constraint";

interface ChipDef {
  kind: Kind;
  label: string;
  type: "decision" | "proactive_finding" | "question" | "finding";
  placeholder: string;
}

const CHIPS: ChipDef[] = [
  { kind: "decision",       label: "+ 共识", type: "decision",         placeholder: "我们达成的共识：…" },
  { kind: "option",         label: "+ 候选", type: "proactive_finding", placeholder: "候选方案 X：…" },
  { kind: "open_question",  label: "+ 待问", type: "question",         placeholder: "还没想清楚的问题：…" },
  { kind: "constraint",     label: "+ 约束", type: "finding",          placeholder: "限制条件：…" },
];

/**
 * Lets the human "promote" an agent's reply into the right-pane via a typed
 * message. The chip click opens an inline editor pre-filled with the agent's
 * body (trimmed) — the user edits it down to the essential line and submits.
 * The right-pane projection picks up the metadata.discussion_kind and
 * inserts it into the matching list.
 */
export function PromoteChips({
  topicId,
  sourceMessageId,
  sourceBody,
}: {
  topicId: number;
  sourceMessageId: number;
  sourceBody: string;
}) {
  const [openKind, setOpenKind] = useState<Kind | null>(null);
  const [draft, setDraft] = useState("");
  const post = usePostMessage(topicId);
  const me = useSessionMe();

  function openEditor(chip: ChipDef) {
    // Default the editor body to a trimmed snippet of the agent reply.
    setDraft(suggestSnippet(sourceBody));
    setOpenKind(chip.kind);
  }

  function cancel() {
    setOpenKind(null);
    setDraft("");
  }

  async function submit() {
    if (!openKind || !me.data) return;
    const trimmed = draft.trim();
    if (!trimmed) return;
    const chip = CHIPS.find((c) => c.kind === openKind);
    if (!chip) return;
    await post.mutateAsync({
      topic_id: topicId,
      type: chip.type,
      actor_type: "human",
      actor_id: me.data.human.id,
      body: trimmed,
      metadata: {
        discussion_kind: openKind,
        promoted_from: sourceMessageId,
      },
    });
    cancel();
  }

  return (
    <div className="mt-2">
      <div className="flex gap-1.5 flex-wrap">
        {CHIPS.map((c) => (
          <button
            key={c.kind}
            type="button"
            onClick={() => openEditor(c)}
            className={[
              "text-[11.5px] px-2.5 py-[3px] rounded-[3px] border transition-colors",
              openKind === c.kind
                ? "bg-accent-soft text-accent-text border-accent-border"
                : "bg-bg text-text-muted border-border hover:bg-surface-elev hover:text-text hover:border-accent-border",
            ].join(" ")}
          >
            {c.label}
          </button>
        ))}
      </div>
      {openKind && (
        <div className="mt-2 border border-border-soft rounded bg-surface-elev p-2 flex flex-col gap-2">
          <textarea
            data-testid="promote-input"
            value={draft}
            autoFocus
            onChange={(e) => setDraft(e.target.value)}
            placeholder={CHIPS.find((c) => c.kind === openKind)?.placeholder}
            rows={2}
            className="bg-transparent outline-none resize-none text-[13px] leading-relaxed"
          />
          <div className="flex justify-end gap-2 items-center">
            <span className="text-[11px] text-text-dim italic mr-auto">
              加入到右栏「
              {openKind === "decision" ? "共识" :
               openKind === "option" ? "候选方案" :
               openKind === "open_question" ? "待回答" : "约束"}
              」
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
            >{post.isPending ? "…" : "确认"}</button>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Heuristic: extract the most "promotable" line from an agent reply.
 * For long bodies the agent often closes with a one-line summary or list
 * item; we use the first non-empty line as the editor's starting point.
 * The user trims/edits before submitting.
 */
function suggestSnippet(body: string): string {
  const lines = body.split("\n").map((l) => l.trim()).filter(Boolean);
  if (lines.length === 0) return "";
  // Drop leading markdown bullet markers / code fences.
  const first = lines[0] ?? "";
  const cleaned = first.replace(/^[-*•]\s*/, "").replace(/^```.*$/, "").trim();
  if (cleaned) return cleaned.length > 120 ? cleaned.slice(0, 120) : cleaned;
  return body.slice(0, 120);
}
