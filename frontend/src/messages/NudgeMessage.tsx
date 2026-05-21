import { useState } from "react";
import type { MessageDTO } from "../api/types";
import { BaseMessage } from "./BaseMessage";
import { useResolveNudge } from "../api/taskTreeQueries";
import { SpinoffDialog } from "../nudge/SpinoffDialog";
import type { NudgeResolution } from "../api/taskTreeTypes";

interface Actor { kind: "system" | "human" | "claude" | "codex"; initial: string; displayName: string }

interface NudgeMeta {
  reason?: string;
  drift_summary?: string;
  drift_nudge_id?: number;
}

export function NudgeMessage({
  message,
  actor,
}: {
  message: MessageDTO;
  actor: Actor;
}) {
  const meta = (message.metadata ?? {}) as NudgeMeta;
  const resolve = useResolveNudge(message.topic_id);
  const [showSpinoff, setShowSpinoff] = useState(false);
  const [resolvedBy, setResolvedBy] = useState<NudgeResolution | null>(null);
  const [spinoffTopicId, setSpinoffTopicId] = useState<number | null>(null);

  if (!meta.drift_nudge_id) {
    // Backward compat: nudge without backing drift_nudges row (legacy fixtures)
    return (
      <BaseMessage
        msgId={message.id} actor={actor}
        timeIso={message.created_at}
        tag="nudge"
        tone="nudge"
        body={<span>{message.body}</span>}
      />
    );
  }

  function doResolve(resolution: NudgeResolution, spinoffTitle?: string) {
    resolve.mutate(
      { id: meta.drift_nudge_id!, resolved_by: resolution, spinoff_title: spinoffTitle },
      {
        onSuccess: (data) => {
          setResolvedBy(resolution);
          if (data?.resolved_to_topic_id) setSpinoffTopicId(data.resolved_to_topic_id);
          setShowSpinoff(false);
        },
      },
    );
  }

  const footer =
    resolvedBy === "dismissed" ? (
      <span className="text-[11px] text-text-dim">已处理：略过</span>
    ) : resolvedBy === "returned" ? (
      <span className="text-[11px] text-text-dim">已处理：回主线</span>
    ) : resolvedBy === "moved_to_topic" ? (
      <span className="text-[11px] text-text-dim">
        已处理：迁移到 topic #{spinoffTopicId}
      </span>
    ) : null;

  return (
    <>
      <BaseMessage
        actor={actor}
        timeIso={message.created_at}
        tag={`nudge${meta.reason ? ` · ${meta.reason}` : ""}`}
        tone="nudge"
        body={
          <div className="flex flex-col gap-2">
            <span>{message.body}</span>
            {!resolvedBy ? (
              <div className="flex gap-2 items-center flex-wrap">
                <button
                  type="button"
                  onClick={() => setShowSpinoff(true)}
                  className="px-2 py-1 rounded bg-nudge text-bg text-[12px]"
                  disabled={resolve.isPending}
                >
                  独立成新 topic
                </button>
                <button
                  type="button"
                  onClick={() => doResolve("returned")}
                  className="px-2 py-1 rounded border border-border text-[12px]"
                  disabled={resolve.isPending}
                >
                  回主线
                </button>
                <button
                  type="button"
                  onClick={() => doResolve("dismissed")}
                  className="px-2 py-1 rounded border border-border text-[12px]"
                  disabled={resolve.isPending}
                >
                  略过
                </button>
              </div>
            ) : (
              footer
            )}
          </div>
        }
      />
      {showSpinoff && (
        <SpinoffDialog
          suggestedTitle={meta.drift_summary?.slice(0, 24) ?? "新 topic"}
          onSubmit={async (title) => doResolve("moved_to_topic", title)}
          onCancel={() => setShowSpinoff(false)}
        />
      )}
    </>
  );
}
