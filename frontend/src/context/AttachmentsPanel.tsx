import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { apiBlobRequest } from "../api/client";
import { useTopicAttachments, useUploadTopicAttachment } from "../api/queries";
import type { AttachmentDTO } from "../api/types";
import { useIdentity } from "../identity/useIdentity";

export function AttachmentsPanel({ topicId }: { topicId: number }) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const identity = useIdentity();
  const attachments = useTopicAttachments(topicId);
  const upload = useUploadTopicAttachment(topicId);
  const [error, setError] = useState<string | null>(null);
  const [downloadingId, setDownloadingId] = useState<number | null>(null);
  const [openingId, setOpeningId] = useState<number | null>(null);
  const [preview, setPreview] = useState<{ attachment: AttachmentDTO; url: string } | null>(null);

  useEffect(() => () => {
    if (preview) URL.revokeObjectURL(preview.url);
  }, [preview]);

  useEffect(() => {
    if (!preview) return;
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setPreview((current) => {
          if (current) URL.revokeObjectURL(current.url);
          return null;
        });
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [preview]);

  async function uploadFile(file: File | undefined) {
    if (!file) return;
    setError(null);
    try {
      await upload.mutateAsync({ file });
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  async function downloadFile(attachment: AttachmentDTO) {
    setError(null);
    setDownloadingId(attachment.id);
    try {
      const blob = await apiBlobRequest(attachment.download_url, { identity });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = attachment.filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setDownloadingId(null);
    }
  }

  async function openPreview(attachment: AttachmentDTO) {
    setError(null);
    setOpeningId(attachment.id);
    try {
      const blob = await apiBlobRequest(attachment.download_url, { identity });
      const url = URL.createObjectURL(blob);
      setPreview((current) => {
        if (current) URL.revokeObjectURL(current.url);
        return { attachment, url };
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setOpeningId(null);
    }
  }

  function closePreview() {
    setPreview((current) => {
      if (current) URL.revokeObjectURL(current.url);
      return null;
    });
  }

  const rows = attachments.data ?? [];

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between gap-2">
        <div className="min-w-0 text-[11px] leading-snug text-text-dim">
          文件会进入当前话题的共享上下文。
        </div>
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          disabled={upload.isPending}
          className="shrink-0 rounded-[3px] border border-border-soft px-2 py-1 text-[11.5px] text-text-dim hover:border-border hover:text-text disabled:opacity-50"
        >
          {upload.isPending ? "上传中" : "上传"}
        </button>
        <input
          ref={inputRef}
          type="file"
          aria-label="选择共享文件"
          className="sr-only"
          onChange={(event) => uploadFile(event.currentTarget.files?.[0])}
        />
      </div>

      {attachments.isLoading ? (
        <div className="rounded border border-border-soft bg-surface-elev px-2 py-2 text-[11.5px] text-text-dim">
          加载中…
        </div>
      ) : rows.length === 0 ? (
        <div className="rounded border border-border-soft bg-surface-elev px-2 py-2 text-[11.5px] text-text-dim">
          还没有共享文件。
        </div>
      ) : (
        <div className="flex flex-col gap-1.5">
          {rows.map((attachment) => {
            const canPreview = isImageAttachment(attachment);
            return (
              <div
                key={attachment.id}
                className="rounded border border-border-soft bg-surface-elev px-2 py-1.5"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="truncate text-[12px] font-medium text-text">
                      {attachment.kind === "image" ? "图片" : "文件"} · {attachment.filename}
                    </div>
                    <div className="mt-0.5 truncate text-[10.5px] text-text-dim">
                      {formatBytes(attachment.byte_size)} · {attachment.mime_type}
                    </div>
                  </div>
                  <div className="flex shrink-0 items-center gap-1">
                    {canPreview && (
                      <button
                        type="button"
                        onClick={() => openPreview(attachment)}
                        disabled={openingId === attachment.id}
                        className="rounded-[3px] border border-border-soft px-2 py-0.5 text-[11px] text-text-dim hover:border-border hover:text-text disabled:opacity-50"
                      >
                        {openingId === attachment.id ? "打开中" : "查看"}
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => downloadFile(attachment)}
                      disabled={downloadingId === attachment.id}
                      className="rounded-[3px] border border-border-soft px-2 py-0.5 text-[11px] text-text-dim hover:border-border hover:text-text disabled:opacity-50"
                    >
                      {downloadingId === attachment.id ? "下载中" : "下载"}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {error && <div className="text-[11.5px] text-accent-text">失败：{error}</div>}

      {preview && createPortal(
        <>
          <button
            type="button"
            aria-label="关闭图片预览"
            className="fixed inset-0 z-30 cursor-default bg-transparent"
            onClick={closePreview}
          />
          <aside
            className="fixed bottom-0 right-0 top-0 z-40 flex w-[min(70vw,860px)] flex-col border-l border-border bg-bg shadow-[-12px_0_30px_-12px_rgba(0,0,0,0.15)] animate-slide-in-right"
            role="dialog"
            aria-label={`查看图片 ${preview.attachment.filename}`}
          >
            <header className="flex h-[42px] shrink-0 items-center justify-between gap-3 border-b border-border-soft px-4">
              <div className="min-w-0">
                <div className="truncate text-[12px] font-mono uppercase tracking-[0.06em] text-text-dim">
                  {preview.attachment.filename}
                </div>
                <div className="truncate text-[10.5px] text-text-dim">
                  {formatBytes(preview.attachment.byte_size)} · {preview.attachment.mime_type}
                </div>
              </div>
              <button
                type="button"
                onClick={closePreview}
                className="shrink-0 px-1 font-mono text-text-dim hover:text-text"
                title="关闭 (Esc)"
                aria-label="close"
              >
                ×
              </button>
            </header>
            <div className="flex min-h-0 flex-1 items-center justify-center overflow-auto p-5">
              <div className="flex min-h-full w-full items-center justify-center rounded border border-border-soft bg-surface-elev p-3">
                <img
                  src={preview.url}
                  alt={preview.attachment.filename}
                  className="max-h-[calc(100vh-90px)] max-w-full object-contain"
                />
              </div>
            </div>
          </aside>
        </>,
        document.body,
      )}
    </div>
  );
}

function isImageAttachment(attachment: AttachmentDTO) {
  return attachment.kind === "image" || attachment.mime_type.startsWith("image/");
}

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  const kb = bytes / 1024;
  if (kb < 1024) return `${kb.toFixed(kb >= 10 ? 0 : 1)} KB`;
  const mb = kb / 1024;
  return `${mb.toFixed(mb >= 10 ? 0 : 1)} MB`;
}
