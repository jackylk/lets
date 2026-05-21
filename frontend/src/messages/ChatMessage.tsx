import type { ReactNode } from "react";
import type { MessageDTO } from "../api/types";
import { BaseMessage } from "./BaseMessage";
import { MentionText } from "./MentionText";
import { PromoteChips } from "./PromoteChips";
import { Provenance } from "./Provenance";
import { MermaidBlock } from "./MermaidBlock";
import { TableBlock, splitTables } from "./TableBlock";
import { Annotatable } from "./Annotatable";
import { AnnotationPins } from "./AnnotationPins";
import { ScoreRow } from "./ScoreRow";
import { useStream } from "./StreamContext";

interface Actor { kind: "human" | "claude" | "codex" | "system"; initial: string; displayName: string }

const BOLD_RE = /\*\*([^*\n]+)\*\*/g;
const CODE_RE = /`([^`\n]+)`/g;
const MERMAID_RE = /```mermaid\s*\n([\s\S]*?)```/g;

/** Split a body into mermaid-block segments + prose segments. */
function splitMermaid(body: string): Array<{ kind: "text" | "mermaid"; value: string }> {
  const out: Array<{ kind: "text" | "mermaid"; value: string }> = [];
  let cursor = 0;
  for (const m of body.matchAll(MERMAID_RE)) {
    const idx = m.index ?? 0;
    if (idx > cursor) out.push({ kind: "text", value: body.slice(cursor, idx) });
    out.push({ kind: "mermaid", value: m[1] ?? "" });
    cursor = idx + m[0].length;
  }
  if (cursor < body.length) out.push({ kind: "text", value: body.slice(cursor) });
  if (out.length === 0) out.push({ kind: "text", value: body });
  return out;
}

/**
 * Render a chat-body line: preserve newlines (caller wraps in whitespace-pre-wrap),
 * highlight @mentions, and pick up two pieces of inline markdown that show up
 * constantly in agent replies — **bold** and `code`.
 */
function renderInline(text: string): ReactNode[] {
  const matches: { idx: number; len: number; kind: "bold" | "code"; inner: string }[] = [];
  for (const m of text.matchAll(BOLD_RE)) {
    matches.push({ idx: m.index ?? 0, len: m[0].length, kind: "bold", inner: m[1] ?? "" });
  }
  for (const m of text.matchAll(CODE_RE)) {
    matches.push({ idx: m.index ?? 0, len: m[0].length, kind: "code", inner: m[1] ?? "" });
  }
  matches.sort((a, b) => a.idx - b.idx);

  const tokens: { kind: "text" | "bold" | "code"; value: string }[] = [];
  let cursor = 0;
  for (const m of matches) {
    if (m.idx < cursor) continue;
    if (m.idx > cursor) tokens.push({ kind: "text", value: text.slice(cursor, m.idx) });
    tokens.push({ kind: m.kind, value: m.inner });
    cursor = m.idx + m.len;
  }
  if (cursor < text.length) tokens.push({ kind: "text", value: text.slice(cursor) });

  const out: ReactNode[] = [];
  tokens.forEach((t, i) => {
    if (t.kind === "text") {
      out.push(<MentionText key={i}>{t.value}</MentionText>);
    } else if (t.kind === "bold") {
      out.push(
        <strong key={i} className="font-semibold">
          <MentionText>{t.value}</MentionText>
        </strong>,
      );
    } else {
      out.push(
        <code key={i} className="font-mono text-[12.5px] bg-surface-hover px-1 rounded">
          {t.value}
        </code>,
      );
    }
  });
  return out;
}

function renderTextSegment(value: string, keyBase: string): ReactNode[] {
  // A "text" segment from splitMermaid may itself contain markdown tables.
  // Pull those out so they render as real tables instead of being mangled
  // by whitespace-pre-wrap.
  const subs = splitTables(value);
  return subs.map((s, j) => {
    const key = `${keyBase}-${j}`;
    if (s.kind === "table") {
      return <TableBlock key={key} table={s.table} renderCell={(t) => renderInline(t)} />;
    }
    return (
      <div key={key} className="whitespace-pre-wrap break-words">
        {renderInline(s.value)}
      </div>
    );
  });
}

export function ChatMessage({ message, actor }: { message: MessageDTO; actor: Actor }) {
  const isAgent = actor.kind === "claude" || actor.kind === "codex";
  const cites = extractCites(message.metadata);
  const segments = splitMermaid(message.body);
  const { viewMode, toggleExpanded } = useStream();
  // When global mode is "collapsed" and this message is rendered as
  // full ChatMessage, the user manually expanded it — offer a "收起" link.
  const showCollapseLink = isAgent && viewMode === "collapsed";
  return (
    <BaseMessage
      msgId={message.id}
      actor={actor}
      timeIso={message.created_at}
      body={
        <div>
          {showCollapseLink && (
            <div className="flex justify-end mb-1">
              <button
                type="button"
                onClick={() => toggleExpanded(message.id)}
                className="text-[10.5px] text-text-dim hover:text-text font-mono uppercase tracking-[0.04em]"
              >收起</button>
            </div>
          )}
          {isAgent && cites.length > 0 && <Provenance cites={cites} />}
          {isAgent ? (
            <Annotatable topicId={message.topic_id} targetMessageId={message.id}>
              {segments.map((seg, i) =>
                seg.kind === "mermaid" ? (
                  <MermaidBlock key={i} source={seg.value} fromMsgId={message.id} topicId={message.topic_id} />
                ) : (
                  <div key={i}>{renderTextSegment(seg.value, String(i))}</div>
                ),
              )}
            </Annotatable>
          ) : (
            segments.map((seg, i) =>
              seg.kind === "mermaid" ? (
                <MermaidBlock key={i} source={seg.value} />
              ) : (
                <div key={i}>{renderTextSegment(seg.value, String(i))}</div>
              ),
            )
          )}
          {isAgent && (
            <>
              <AnnotationPins topicId={message.topic_id} messageId={message.id} />
              <ScoreRow topicId={message.topic_id} messageId={message.id} />
              <PromoteChips
                topicId={message.topic_id}
                sourceMessageId={message.id}
                sourceBody={message.body}
              />
            </>
          )}
        </div>
      }
    />
  );
}

function extractCites(meta: unknown): number[] {
  if (typeof meta !== "object" || meta === null) return [];
  const raw = (meta as Record<string, unknown>).cites;
  if (!Array.isArray(raw)) return [];
  return raw.filter((n): n is number => typeof n === "number");
}
