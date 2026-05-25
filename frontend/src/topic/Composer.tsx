import { useEffect, useMemo, useRef, useState, type ChangeEvent, type KeyboardEvent, type ReactNode } from "react";

export interface ComposerMessage {
  body: string;
  /** Comma-separated typed addressees, e.g. human:2,agent:7. */
  addressedTo: string | null;
}

export interface MentionResolver {
  resolveAddresses?: (mentions: string[]) => string[];
  /** @deprecated Use resolveAddresses so agents can be addressed as agent:<id>. */
  resolveHumanIds: (mentions: string[]) => number[];
}

export interface MentionCandidate {
  key: string;
  label: string;
  detail: string;
  kind: "human" | "agent";
}

interface Props {
  onSend: (msg: ComposerMessage) => void;
  onAttachFile?: (file: File) => void | Promise<void>;
  resolver?: MentionResolver;
  mentionCandidates?: MentionCandidate[];
  placeholder?: string;
  disabled?: boolean;
  attachmentDisabled?: boolean;
  statusSlot?: ReactNode;
}

/**
 * Parses `@name` / `@cc` / `@codex` tokens out of the body and asks the
 * resolver to map them to typed addressees. The result is stuffed into
 * ``addressed_to`` on the outgoing message — humans use human:<id>,
 * agents use agent:<id>.
 */
function extractMentions(body: string): string[] {
  const matches = body.matchAll(/@([\p{L}\p{N}_-]+)/gu);
  const out = new Set<string>();
  for (const m of matches) {
    out.add(m[1]!.toLowerCase());
  }
  const lowered = body.toLowerCase();
  if (/(^|[^\p{L}\p{N}_-])(cc|claude)(?=$|[^\p{L}\p{N}_-]|[\u4e00-\u9fff])/u.test(lowered)) {
    out.add("cc");
  }
  if (/(^|[^\p{L}\p{N}_-])(cx|codex)(?=$|[^\p{L}\p{N}_-]|[\u4e00-\u9fff])/u.test(lowered)) {
    out.add("cx");
  }
  return [...out];
}

function activeMentionQuery(text: string, caret: number): { start: number; query: string } | null {
  const before = text.slice(0, caret);
  const match = before.match(/@([\p{L}\p{N}_-]*)$/u);
  if (!match || match.index == null) return null;
  return { start: match.index, query: (match[1] ?? "").toLowerCase() };
}

export function Composer({
  onSend,
  onAttachFile,
  resolver,
  mentionCandidates = [],
  placeholder,
  disabled,
  attachmentDisabled,
  statusSlot,
}: Props) {
  const [text, setText] = useState("");
  const [caret, setCaret] = useState(0);
  const [activeIndex, setActiveIndex] = useState(0);
  const [attachBusy, setAttachBusy] = useState(false);
  const [attachStatus, setAttachStatus] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const pendingCaretRef = useRef<number | null>(null);

  const mentionQuery = activeMentionQuery(text, caret);
  const mentionOptions = useMemo(() => {
    if (!mentionQuery) return [];
    const q = mentionQuery.query;
    // Empty query (just typed "@") → show everything in stable order.
    if (q === "") return mentionCandidates.slice(0, 6);
    // Prefix match on key (e.g. "cc", "codex", "jacky") OR on label, with
    // a tier so key-prefix matches rank above label-prefix matches.
    const ranked: { c: MentionCandidate; tier: number }[] = [];
    for (const c of mentionCandidates) {
      const key = c.key.toLowerCase();
      const label = c.label.toLowerCase();
      if (key.startsWith(q)) ranked.push({ c, tier: 0 });
      else if (label.startsWith(q)) ranked.push({ c, tier: 1 });
      // Also tolerate the user typing inside the label after a space —
      // e.g. "@mac" should still find "claude · mac16".
      else if (label.split(/[\s·]+/).some((part) => part.startsWith(q))) {
        ranked.push({ c, tier: 2 });
      }
    }
    ranked.sort((a, b) => a.tier - b.tier);
    return ranked.map((r) => r.c).slice(0, 6);
  }, [mentionCandidates, mentionQuery]);

  useEffect(() => {
    const nextCaret = pendingCaretRef.current;
    if (nextCaret === null) return;
    pendingCaretRef.current = null;
    textareaRef.current?.focus();
    textareaRef.current?.setSelectionRange(nextCaret, nextCaret);
  }, [text]);

  function updateText(e: ChangeEvent<HTMLTextAreaElement>) {
    setText(e.target.value);
    setCaret(e.target.selectionStart);
    setActiveIndex(0);
  }

  function selectMention(candidate: MentionCandidate) {
    if (!mentionQuery) return;
    const next = `${text.slice(0, mentionQuery.start)}@${candidate.key} ${text.slice(caret)}`;
    const nextCaret = mentionQuery.start + candidate.key.length + 2;
    pendingCaretRef.current = nextCaret;
    setText(next);
    setCaret(nextCaret);
    setActiveIndex(0);
  }

  function submit() {
    const trimmed = text.trim();
    if (!trimmed) return;
    const mentions = extractMentions(trimmed);
    let addressedTo: string | null = null;
    if (mentions.length > 0 && resolver) {
      const addresses = resolver.resolveAddresses
        ? resolver.resolveAddresses(mentions)
        : resolver.resolveHumanIds(mentions).map((id) => String(id));
      addressedTo = addresses.length > 0 ? addresses.join(",") : null;
    }
    onSend({ body: trimmed, addressedTo });
    setText("");
    setCaret(0);
  }

  async function attachFile(file: File | undefined) {
    if (!file || !onAttachFile) return;
    setAttachBusy(true);
    setAttachStatus(null);
    try {
      await onAttachFile(file);
      setAttachStatus(`已上传 ${file.name}`);
    } catch (e) {
      setAttachStatus(e instanceof Error ? `上传失败：${e.message}` : "上传失败");
    } finally {
      setAttachBusy(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  function onKey(e: KeyboardEvent<HTMLTextAreaElement>) {
    // IME composition: while the user is committing 拼音/汉字/英文候选 via
    // Sogou/Microsoft IME etc., Enter belongs to the IME, not to us. Bail
    // out so the IME picks the candidate normally and we don't send a half-
    // typed message. (e.keyCode === 229 is the legacy signal; isComposing
    // is the modern one — check both.)
    if (e.nativeEvent.isComposing || e.keyCode === 229) {
      return;
    }
    if (mentionOptions.length > 0) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setActiveIndex((i) => (i + 1) % mentionOptions.length);
        return;
      }
      if (e.key === "ArrowUp") {
        e.preventDefault();
        setActiveIndex((i) => (i - 1 + mentionOptions.length) % mentionOptions.length);
        return;
      }
      if (e.key === "Tab" || e.key === "Enter") {
        e.preventDefault();
        const selected = mentionOptions[activeIndex] ?? mentionOptions[0];
        if (selected) selectMention(selected);
        return;
      }
      if (e.key === "Escape") {
        setCaret(0);
        return;
      }
    }
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  const mentions = extractMentions(text);
  const resolvedAddresses =
    mentions.length > 0 && resolver
      ? resolver.resolveAddresses
        ? resolver.resolveAddresses(mentions)
        : resolver.resolveHumanIds(mentions).map((id) => String(id))
      : [];
  const isChoosingMention = mentionQuery !== null && mentionOptions.length > 0;

  return (
    <div className="px-3 py-2 md:px-6 md:py-3 border-t border-border-soft bg-bg">
      {statusSlot}
      <div className="relative rounded border border-border bg-surface-elev px-3 py-2 flex flex-col gap-2 shadow-sm focus-within:border-accent-border focus-within:shadow-[0_0_0_3px_var(--color-accent-soft)]">
        {mentionOptions.length > 0 && (
          <div className="absolute left-3 bottom-[calc(100%+6px)] w-72 max-w-[calc(100vw-48px)] rounded border border-border bg-surface-elev shadow-lg overflow-hidden z-20">
            {mentionOptions.map((candidate, index) => (
              <button
                key={`${candidate.kind}-${candidate.key}`}
                type="button"
                onMouseDown={(e) => {
                  e.preventDefault();
                  selectMention(candidate);
                }}
                className={[
                  "w-full px-3 py-2 text-left flex items-center gap-2 transition-colors",
                  index === activeIndex
                    ? "bg-accent-soft shadow-[inset_2px_0_0_var(--color-accent)]"
                    : "hover:bg-surface-hover",
                ].join(" ")}
              >
                <span className="w-7 h-7 rounded-[3px] border border-border grid place-items-center font-[var(--font-display)] text-[12px] text-text-muted">
                  {candidate.kind === "agent" ? candidate.key.toUpperCase().slice(0, 2) : candidate.label.slice(0, 1).toUpperCase()}
                </span>
                <span className="min-w-0">
                  <span className="block text-[13px] text-text truncate">{candidate.label}</span>
                  <span className="block text-[11px] text-text-dim font-mono truncate">@{candidate.key} · {candidate.detail}</span>
                </span>
              </button>
            ))}
          </div>
        )}
        <textarea
          data-testid="composer-textarea"
          ref={textareaRef}
          rows={1}
          value={text}
          disabled={disabled}
          placeholder={placeholder ?? "发消息，输入 @ 选择人或 agent…"}
          onChange={updateText}
          onSelect={(e) => setCaret(e.currentTarget.selectionStart)}
          onClick={(e) => setCaret(e.currentTarget.selectionStart)}
          onKeyDown={onKey}
          className="bg-transparent outline-none resize-none text-[16px] md:text-[14.5px] leading-relaxed min-h-[34px] md:min-h-[28px]"
        />
        <div className="flex items-center text-[11px] text-text-dim gap-2">
          <span className="hidden sm:inline">/ 命令 · @ 提及 · Enter 发送 · Shift Enter 换行</span>
          <span className="sm:hidden">@ 提及 · 换行用 Shift Enter</span>
          {mentions.length > 0 && (
            <span className="font-mono">
              {mentions.map((m) => `@${m}`).join(" ")}
              {resolvedAddresses.length > 0
                ? ` to ${resolvedAddresses.join(",")}`
                : isChoosingMention ? "" : " (无法解析)"}
            </span>
          )}
          {attachStatus && (
            <span className="min-w-0 truncate text-text-dim">{attachStatus}</span>
          )}
          <div className="flex-1" />
          {onAttachFile && (
            <>
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={disabled || attachmentDisabled || attachBusy}
                className="rounded-[3px] border border-border-soft px-2.5 py-1 md:py-0.5 text-[12px] text-text-dim hover:border-border hover:text-text disabled:cursor-not-allowed disabled:opacity-40"
              >
                {attachBusy ? "上传中" : "附件"}
              </button>
              <input
                ref={fileInputRef}
                type="file"
                aria-label="添加附件"
                className="sr-only"
                onChange={(event) => void attachFile(event.currentTarget.files?.[0])}
              />
            </>
          )}
          <button
            type="button"
            onClick={submit}
            disabled={!text.trim() || disabled}
            className="px-3 py-1.5 md:py-1 rounded-[3px] bg-text text-bg disabled:opacity-40 disabled:cursor-not-allowed text-[12px] font-medium"
          >
            发送
          </button>
        </div>
      </div>
    </div>
  );
}
