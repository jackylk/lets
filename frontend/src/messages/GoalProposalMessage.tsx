import { useState } from "react";
import type { MessageDTO } from "../api/types";
import { BaseMessage } from "./BaseMessage";
import { useAdoptGoalProposal } from "../api/taskTreeQueries";

interface Actor {
  kind: "human" | "claude" | "codex" | "system";
  initial: string;
  displayName: string;
}

interface GoalProposalMeta {
  artifact_id?: number | null;
  spec_text?: string;
}

export function GoalProposalMessage({
  message,
  actor,
}: {
  message: MessageDTO;
  actor: Actor;
}) {
  const meta = (message.metadata ?? {}) as GoalProposalMeta;
  const adopt = useAdoptGoalProposal(message.topic_id);
  const [adopted, setAdopted] = useState(false);

  function handleAdopt() {
    adopt.mutate(
      { goal_proposal_message_id: message.id },
      { onSuccess: () => setAdopted(true) },
    );
  }

  return (
    <BaseMessage
      actor={actor}
      timeIso={message.created_at}
      tag="goal_proposal"
      tone="spec"
      body={
        <div className="flex flex-col gap-2">
          {meta.artifact_id && (
            <div className="font-mono text-[12px] text-text-muted">
              artifact#{meta.artifact_id}
            </div>
          )}
          <div className="text-[13px]">{message.body}</div>
          <div className="flex items-center gap-2 mt-1">
            <div className="flex-1" />
            {adopted ? (
              <span className="text-[12px] text-status-on font-medium">
                Adopted ✓
              </span>
            ) : (
              <button
                type="button"
                onClick={handleAdopt}
                disabled={adopt.isPending}
                className="px-2 py-1 rounded bg-spec text-bg text-[12px] font-medium disabled:opacity-40"
              >
                Set as goal
              </button>
            )}
          </div>
        </div>
      }
    />
  );
}
