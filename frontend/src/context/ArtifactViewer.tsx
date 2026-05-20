import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useIdentity } from "../identity/useIdentity";
import { apiRequest } from "../api/client";
import type { ArtifactDTO } from "../api/types";
import { cn } from "../lib/cn";

interface Props {
  artifact: ArtifactDTO;
  onClose: () => void;
}

interface ReadResponse {
  artifact: ArtifactDTO;
  content_b64: string;
  current_version_label: string | null;
}

/**
 * Modal viewer for an artifact's text content. Defaults to the latest
 * version; the user can switch to any prior version via the chip row.
 * The viewer assumes UTF-8 text (markdown / outline / code); binary
 * artifacts would need a different renderer.
 */
export function ArtifactViewer({ artifact, onClose }: Props) {
  const identity = useIdentity();
  const sortedVersions = useMemo(
    () => [...(artifact.versions ?? [])].sort((a, b) => a.id - b.id),
    [artifact.versions],
  );
  const latestLabel =
    sortedVersions[sortedVersions.length - 1]?.version_label ?? null;
  const [versionLabel, setVersionLabel] = useState<string | null>(latestLabel);

  const read = useQuery({
    queryKey: ["artifact", artifact.id, "content", versionLabel],
    queryFn: () =>
      apiRequest<ReadResponse>(
        `/api/artifacts/${artifact.id}${
          versionLabel ? `?version_label=${encodeURIComponent(versionLabel)}` : ""
        }`,
        { identity },
      ),
  });

  // Close on Escape
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const content = useMemo(() => {
    if (!read.data?.content_b64) return "";
    try {
      // atob → binary string → percent-encode → decodeURIComponent for UTF-8
      const raw = atob(read.data.content_b64);
      const bytes = new Uint8Array(raw.length);
      for (let i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i);
      return new TextDecoder("utf-8").decode(bytes);
    } catch {
      return "<failed to decode>";
    }
  }, [read.data]);

  return (
    <div
      className="fixed inset-0 z-50 bg-text/30 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={`Artifact viewer: ${artifact.slug}`}
        className="bg-surface-elev rounded-lg max-w-3xl w-full max-h-[80vh] flex flex-col border border-border-soft shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-center gap-3 px-4 py-3 border-b border-border-soft">
          <div className="flex flex-col min-w-0">
            <div className="text-[11px] uppercase tracking-wider text-text-dim font-semibold">
              交付物
            </div>
            <div className="font-mono text-[14px] truncate">{artifact.slug}</div>
          </div>
          <div className="flex-1" />
          <div className="flex gap-1">
            {sortedVersions.map((v) => (
              <button
                key={v.id}
                type="button"
                onClick={() => setVersionLabel(v.version_label)}
                className={cn(
                  "text-[11px] font-mono px-2 py-1 rounded transition-colors",
                  versionLabel === v.version_label
                    ? "bg-artifact text-bg"
                    : "bg-surface text-text-muted hover:bg-surface-hover",
                )}
                title={v.summary ?? undefined}
              >
                {v.version_label}
              </button>
            ))}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="ml-2 w-7 h-7 grid place-items-center rounded hover:bg-surface-hover text-text-muted"
            aria-label="close"
          >
            ✕
          </button>
        </header>

        <div className="flex-1 overflow-auto p-4">
          {read.isLoading ? (
            <div className="text-text-dim text-sm">加载中…</div>
          ) : read.isError ? (
            <div className="text-text-dim text-sm">加载失败</div>
          ) : (
            <pre className="text-[12.5px] leading-relaxed whitespace-pre-wrap font-mono text-text">
              {content}
            </pre>
          )}
        </div>

        <footer className="px-4 py-2 border-t border-border-soft flex items-center gap-2 text-[11px] text-text-dim font-mono">
          <span>{artifact.backend}</span>
          <span>·</span>
          <span className="truncate">{artifact.backend_ref}</span>
          <span className="flex-1" />
          {read.data?.current_version_label && (
            <span>当前 {read.data.current_version_label}</span>
          )}
        </footer>
      </div>
    </div>
  );
}
