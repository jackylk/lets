import { useState, type KeyboardEvent } from "react";

export interface ComposerMessage {
  body: string;
  /** Comma-separated human IDs derived from @mentions in the body. */
  addressedTo: string | null;
}

export interface MentionResolver {
  resolveHumanIds: (mentions: string[]) => number[];
}

interface Props {
  onSend: (msg: ComposerMessage) => void;
  resolver?: MentionResolver;
  placeholder?: string;
  disabled?: boolean;
}

/**
 * Parses `@name` / `@cc` / `@codex` tokens out of the body and asks the
 * resolver to map them to human_ids. The result is stuffed into
 * ``addressed_to`` on the outgoing message — which is what the agent
 * runner pivots on to decide whether to invoke the local CLI.
 */
function extractMentions(body: string): string[] {
  const matches = body.matchAll(/@([\p{L}\p{N}_-]+)/gu);
  const out = new Set<string>();
  for (const m of matches) {
    out.add(m[1]!.toLowerCase());
  }
  return [...out];
}

export function Composer({ onSend, resolver, placeholder, disabled }: Props) {
  const [text, setText] = useState("");

  function submit() {
    const trimmed = text.trim();
    if (!trimmed) return;
    const mentions = extractMentions(trimmed);
    let addressedTo: string | null = null;
    if (mentions.length > 0 && resolver) {
      const ids = resolver.resolveHumanIds(mentions);
      addressedTo = ids.length > 0 ? ids.join(",") : null;
    }
    onSend({ body: trimmed, addressedTo });
    setText("");
  }

  function onKey(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  const mentions = extractMentions(text);
  const resolvedIds =
    mentions.length > 0 && resolver ? resolver.resolveHumanIds(mentions) : [];

  return (
    <div className="px-6 py-3">
      <div className="rounded-lg border border-border bg-surface-elev px-3 py-2 flex flex-col gap-2">
        <textarea
          rows={1}
          value={text}
          disabled={disabled}
          placeholder={placeholder ?? "发消息，或 @claude / @codex / @human 派活…"}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKey}
          className="bg-transparent outline-none resize-none text-[14px] leading-relaxed min-h-[28px]"
        />
        <div className="flex items-center text-[11px] text-text-dim gap-2">
          <span>/ 命令 · @ 提及 · ⏎ 发送 · ⇧⏎ 换行</span>
          {mentions.length > 0 && (
            <span className="font-mono">
              {mentions.map((m) => `@${m}`).join(" ")}
              {resolvedIds.length > 0
                ? ` → human_id ${resolvedIds.join(",")}`
                : " (无法解析)"}
            </span>
          )}
          <div className="flex-1" />
          <button
            type="button"
            onClick={submit}
            disabled={!text.trim() || disabled}
            className="px-3 py-1 rounded bg-text text-bg disabled:opacity-40 disabled:cursor-not-allowed text-[12px] font-medium"
          >
            发送
          </button>
        </div>
      </div>
    </div>
  );
}
