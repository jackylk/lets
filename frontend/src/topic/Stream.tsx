import { useEffect } from "react";
import type { MessageDTO } from "../api/types";
import { Message } from "../messages/Message";
import { makeActorResolver, type Directory } from "../messages/actorResolver";
import { useStream } from "../messages/StreamContext";
import { DaySeparator } from "./DaySeparator";
import { ReadCursorLine } from "./ReadCursorLine";
import { parseBackendTs } from "../lib/time";
import { subscribeJumpToMessage } from "../context/jumpToMessage";

interface Props {
  messages: MessageDTO[];
  directory: Directory;
  topicId: number;
}

function dayLabel(iso: string): string {
  return parseBackendTs(iso).toLocaleDateString("zh-CN");
}

const REPLY_TYPES = new Set(["chat", "finding", "decision", "review", "handoff", "artifact_revision", "spec_change"]);

/**
 * Hide "X 正在输入…" status messages once the same agent has actually
 * delivered a reply (or finding) after them — like WhatsApp's typing
 * indicator that disappears once the message arrives. We never hide a
 * status that doesn't yet have a follow-up; the user still sees "working
 * on it" while the agent is still working.
 */
function shouldHide(message: MessageDTO, idx: number, all: MessageDTO[]): boolean {
  // Annotations render as sticky-note pins under their target message.
  if (message.type === "annotation") return true;
  // Pane-update typed messages (carry metadata.discussion_kind) surface in
  // the right pane only — keeping them in chat too would just be noise.
  if (hasDiscussionKind(message.metadata)) return true;
  if (message.type !== "status") return false;
  if (message.actor_type !== "agent") return false;
  const actorId = message.actor_id;
  if (actorId == null) return false;
  for (let j = idx + 1; j < all.length; j++) {
    const next = all[j];
    if (!next) continue;
    if (
      next.actor_type === "agent" &&
      next.actor_id === actorId &&
      REPLY_TYPES.has(next.type)
    ) {
      return true;
    }
  }
  return false;
}

function hasDiscussionKind(meta: unknown): boolean {
  if (typeof meta !== "object" || meta === null) return false;
  return typeof (meta as Record<string, unknown>).discussion_kind === "string";
}

export function Stream({ messages, directory, topicId }: Props) {
  // The caller (TopicView) wraps with StreamProvider so the topic header
  // (ViewModeToggle, sibling of <Stream/>) can share state with messages.
  // We do NOT install another provider here — that would shadow the outer
  // one and split view-mode state in two.
  return <StreamBody messages={messages} directory={directory} topicId={topicId} />;
}

function StreamBody({ messages, directory }: Props) {
  const resolve = makeActorResolver(directory);
  const stream = useStream();
  const { readCursor, viewMode, isExpanded, toggleExpanded, setHighlighted, clearHighlight } = stream;

  // Right-pane card click → scroll the chat to the matching message + flash
  // it. Uses the existing cited-highlight pipeline (BaseMessage paints any
  // id in `highlighted` with the accent stripe). Auto-fades after 2s.
  useEffect(() => {
    return subscribeJumpToMessage((msgId) => {
      // If the message is in this topic (the right pane is per-topic, so
      // normally yes), scroll into view + flash.
      const exists = messages.some((m) => m.id === msgId);
      if (!exists) return;
      // If currently collapsed, expand that message so the user sees its
      // body instead of just the summary line.
      if (viewMode === "collapsed" && !isExpanded(msgId)) {
        toggleExpanded(msgId);
      }
      // Defer the scroll a tick so React has time to mount the expanded form.
      requestAnimationFrame(() => {
        const el = document.querySelector(`[data-msg-id="${msgId}"]`);
        el?.scrollIntoView({ behavior: "smooth", block: "center" });
        setHighlighted([msgId]);
        setTimeout(() => clearHighlight(), 2200);
      });
    });
    // We intentionally bind once per (messages, viewMode) tuple so the closure
    // captures the latest viewMode/isExpanded for the toggle decision.
  }, [messages, viewMode, isExpanded, toggleExpanded, setHighlighted, clearHighlight]);
  let lastDay: string | null = null;
  let cursorRendered = false;

  // In "humans-only" mode, agent chats are skipped from rendering but
  // we keep a thin marker showing how many we elided in each gap. Track
  // pending elisions so consecutive agent posts collapse to a single bar.
  type Row =
    | { kind: "msg"; m: MessageDTO; idx: number }
    | { kind: "elided"; count: number; ids: number[] };
  const rows: Row[] = [];
  for (let i = 0; i < messages.length; i++) {
    const m = messages[i]!;
    if (shouldHide(m, i, messages)) continue;
    const isAgent =
      m.actor_type === "agent" &&
      (m.type === "chat" || m.type === "finding");
    const elide =
      viewMode === "humans-only" && isAgent && !isExpanded(m.id);
    if (elide) {
      const last = rows[rows.length - 1];
      if (last && last.kind === "elided") {
        last.count += 1;
        last.ids.push(m.id);
      } else {
        rows.push({ kind: "elided", count: 1, ids: [m.id] });
      }
    } else {
      rows.push({ kind: "msg", m, idx: i });
    }
  }

  return (
    <div className="flex flex-col">
      {rows.map((r, ri) => {
        if (r.kind === "elided") {
          return (
            <div
              key={`elided-${ri}`}
              className="my-1 flex items-center gap-2 text-[11px] text-text-dim italic px-1"
            >
              <span className="flex-1 border-t border-dashed border-border-soft" />
              <button
                type="button"
                className="text-text-dim hover:text-accent-text font-mono uppercase tracking-[0.04em] not-italic"
                onClick={() => r.ids.forEach(toggleExpanded)}
              >
                Agent 中间说了 {r.count} 条 · 展开
              </button>
              <span className="flex-1 border-t border-dashed border-border-soft" />
            </div>
          );
        }
        const { m } = r;
        const day = dayLabel(m.created_at);
        const showDay = day !== lastDay;
        lastDay = day;
        const showCursor =
          !cursorRendered && readCursor > 0 && m.id > readCursor;
        if (showCursor) cursorRendered = true;
        return (
          <div key={m.id}>
            {showDay && <DaySeparator label={day} />}
            {showCursor && <ReadCursorLine />}
            <Message message={m} resolveActor={resolve} />
          </div>
        );
      })}
    </div>
  );
}
