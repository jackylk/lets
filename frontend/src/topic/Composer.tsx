import { useState, type KeyboardEvent } from "react";

interface Props {
  onSend: (body: string) => void;
  placeholder?: string;
  disabled?: boolean;
}

export function Composer({ onSend, placeholder, disabled }: Props) {
  const [text, setText] = useState("");

  function submit() {
    const trimmed = text.trim();
    if (!trimmed) return;
    onSend(trimmed);
    setText("");
  }

  function onKey(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

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
        <div className="flex items-center text-[11px] text-text-dim">
          <span>/ 命令 · @ 提及 · ⏎ 发送 · ⇧⏎ 换行</span>
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
