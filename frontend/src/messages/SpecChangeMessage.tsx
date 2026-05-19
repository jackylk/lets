import type { MessageDTO, SpecChangeMeta } from "../api/types";
import { BaseMessage } from "./BaseMessage";

interface Actor { kind: "human" | "claude" | "codex" | "system"; initial: string; displayName: string }

export function SpecChangeMessage({ message, actor }: { message: MessageDTO; actor: Actor }) {
  const meta = message.metadata as Partial<SpecChangeMeta>;
  return (
    <BaseMessage
      actor={actor}
      timeIso={message.created_at}
      tag="spec_change"
      tone="spec"
      body={
        <div className="flex flex-col gap-2">
          <div className="font-mono text-[12px] text-text-muted">{meta.file ?? "?"}</div>
          <div className="text-[13px]">{message.body}</div>
          <div className="flex items-center gap-2 text-[12px]">
            <span className="font-mono px-1.5 py-px rounded bg-finding-bg text-finding">{String(meta.before ?? "-")}</span>
            <span className="text-text-dim">→</span>
            <span className="font-mono px-1.5 py-px rounded bg-spec-bg text-spec">{String(meta.after ?? "-")}</span>
          </div>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-[11px] text-text-muted">approvers:</span>
            {(meta.approvers ?? []).length === 0 ? (
              <span className="text-[11px] text-text-dim italic">none yet</span>
            ) : (
              meta.approvers!.map((name) => (
                <span key={name} className="text-[11px] px-1.5 py-px bg-surface rounded font-mono">{name}</span>
              ))
            )}
            <div className="flex-1" />
            <button type="button" className="px-2 py-1 rounded bg-spec text-bg text-[12px] font-medium">
              Approve
            </button>
            <button type="button" className="px-2 py-1 rounded border border-border text-[12px]">
              See diff
            </button>
          </div>
        </div>
      }
    />
  );
}
