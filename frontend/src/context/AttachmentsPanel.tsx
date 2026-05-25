import { useRef, useState } from "react";
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
          {rows.map((attachment) => (
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
                <button
                  type="button"
                  onClick={() => downloadFile(attachment)}
                  disabled={downloadingId === attachment.id}
                  className="shrink-0 rounded-[3px] border border-border-soft px-2 py-0.5 text-[11px] text-text-dim hover:border-border hover:text-text disabled:opacity-50"
                >
                  {downloadingId === attachment.id ? "下载中" : "下载"}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {error && <div className="text-[11.5px] text-accent-text">失败：{error}</div>}
    </div>
  );
}

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  const kb = bytes / 1024;
  if (kb < 1024) return `${kb.toFixed(kb >= 10 ? 0 : 1)} KB`;
  const mb = kb / 1024;
  return `${mb.toFixed(mb >= 10 ? 0 : 1)} MB`;
}
