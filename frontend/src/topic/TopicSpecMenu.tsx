import { useEffect, useRef, useState } from "react";
import { apiRequest } from "../api/client";
import { useIdentity } from "../identity/useIdentity";

export function TopicSpecMenu({ topicId }: { topicId: number }) {
  const identity = useIdentity();
  const rootRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    function onPointerDown(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  async function shareUrl() {
    const data = await apiRequest<{ url: string }>(`/api/topics/${topicId}/share`, {
      method: "POST",
      body: { reuse_existing: true },
      identity,
    });
    return data.url;
  }

  async function openSpec() {
    setBusy(true);
    setStatus(null);
    try {
      const url = await shareUrl();
      await navigator.clipboard?.writeText(url);
      window.open(url, "_blank", "noopener,noreferrer");
      setOpen(false);
    } catch (e) {
      setStatus(`Spec 失败：${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label="topic menu"
        aria-expanded={open}
        className="px-2 py-1 rounded-[3px] hover:bg-surface-hover text-text-muted"
      >
        ⋯
      </button>
      {open && (
        <div className="absolute right-0 top-8 z-30 w-44 rounded-md border border-border bg-surface-elev p-1 shadow-[0_12px_32px_rgba(44,42,38,0.14)]">
          <SpecMenuItem onClick={openSpec} disabled={busy}>
            {busy ? "打开中…" : "Spec"}
          </SpecMenuItem>
          <div className="px-2.5 pb-1.5 text-[10.5px] leading-snug text-text-dim">
            打开在线页并复制共享链接；页面内可下载 Markdown。
          </div>
          {status && (
            <div className="px-2.5 py-1.5 text-[11px] text-text-dim">
              {status}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function SpecMenuItem({
  children,
  onClick,
  disabled,
}: {
  children: string;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={() => void onClick()}
      className="flex w-full items-center rounded px-2.5 py-1.5 text-left text-[12.5px] text-text-muted hover:bg-surface-hover hover:text-text disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:bg-transparent"
    >
      {children}
    </button>
  );
}
