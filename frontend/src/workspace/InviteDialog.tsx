import { useEffect, useRef, useState } from "react";

interface Props {
  workspaceName: string;
  topicTitle?: string | null;
  joinUrl: string;
  onClose: () => void;
}

async function copyText(value: string) {
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(value);
      return true;
    } catch {
      // Fall through to the selection-based fallback below.
    }
  }

  const textarea = document.createElement("textarea");
  textarea.value = value;
  textarea.setAttribute("readonly", "true");
  textarea.style.position = "fixed";
  textarea.style.left = "-9999px";
  document.body.appendChild(textarea);
  textarea.select();
  try {
    return document.execCommand?.("copy") === true;
  } finally {
    document.body.removeChild(textarea);
  }
}

export function InviteDialog({ workspaceName, topicTitle, joinUrl, onClose }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [copyState, setCopyState] = useState<"idle" | "copied" | "failed">("idle");

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  const onCopy = async () => {
    const ok = await copyText(joinUrl);
    if (ok) {
      setCopyState("copied");
      window.setTimeout(() => setCopyState("idle"), 1600);
      return;
    }
    inputRef.current?.select();
    setCopyState("failed");
  };

  return (
    <div
      className="fixed inset-0 z-50 grid place-items-center bg-black/40 px-4"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="invite-dialog-title"
        onMouseDown={(event) => event.stopPropagation()}
        className="w-full max-w-md rounded border border-border bg-bg p-6 shadow-[0_18px_56px_rgba(44,42,38,0.18)]"
      >
        <h2
          id="invite-dialog-title"
          className="mb-3 font-[var(--font-display)] text-lg text-text"
        >
          {topicTitle
            ? `邀请同事加入「${topicTitle}」`
            : `邀请成员加入「${workspaceName}」`}
        </h2>
        <p className="mb-4 text-sm leading-6 text-text-dim">
          {topicTitle
            ? `复制链接发给对方。对方会加入「${workspaceName}」，并直接进入这个话题。`
            : "复制这个邀请链接发给对方。对方输入显示名即可作为访客加入，也可以用 GitHub 继续。"}
        </p>

        <div className="mb-4 rounded border border-border bg-surface-elev p-2.5">
          <div className="flex items-center gap-2">
            <input
              ref={inputRef}
              id="invite-url"
              aria-label="邀请链接"
              readOnly
              value={joinUrl}
              onFocus={(event) => event.currentTarget.select()}
              className="min-w-0 flex-1 bg-transparent font-mono text-[13px] text-text outline-none"
            />
            <button
              type="button"
              onClick={onCopy}
              className="shrink-0 rounded bg-text px-2.5 py-1 text-[12px] font-medium text-bg hover:opacity-90"
            >
              {copyState === "copied" ? "已复制" : "复制"}
            </button>
          </div>
        </div>
        {copyState === "failed" && (
          <div className="-mt-2 mb-4 text-[11px] text-text-dim">
            浏览器没有允许自动复制，链接已选中，可以按 Cmd/Ctrl+C。
          </div>
        )}

        <div className="flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="rounded bg-text px-3 py-1.5 text-[13px] font-medium text-bg hover:opacity-90"
          >
            完成
          </button>
        </div>
      </div>
    </div>
  );
}
