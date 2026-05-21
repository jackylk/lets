import { useState } from "react";
import { useIdentity } from "../identity/useIdentity";

/**
 * Header button: fetch the rendered spec markdown for this topic and
 * trigger a browser download. Same projection as `lets spec <id>` on the
 * CLI — the endpoint is `/api/topics/{id}/spec` and returns text/markdown
 * with content-disposition set, so the browser handles the save dialog.
 */
export function ExportSpecButton({ topicId }: { topicId: number }) {
  const identity = useIdentity();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function download() {
    setBusy(true);
    setError(null);
    try {
      const headers: Record<string, string> = {};
      if (identity.humanName) headers["X-Lets-Human"] = identity.humanName;
      if (identity.agentRole) headers["X-Lets-Agent-Role"] = identity.agentRole;
      if (identity.deviceLabel) headers["X-Lets-Device"] = identity.deviceLabel;
      const res = await fetch(`/api/topics/${topicId}/spec`, { headers });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `topic-${topicId}-spec.md`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <button
      type="button"
      onClick={download}
      disabled={busy}
      title={
        error
          ? `导出失败：${error}`
          : "把当前讨论凝结成 markdown spec — 可直接喂给其他 agent"
      }
      className={
        "px-2.5 py-1 rounded-[3px] border border-border-soft text-[11.5px] font-mono uppercase tracking-[0.04em] " +
        (error
          ? "text-accent-text border-accent-border"
          : "text-text-dim hover:text-text hover:border-border")
      }
    >
      {busy ? "…" : "导出 spec"}
    </button>
  );
}
