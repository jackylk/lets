import type { MessageDTO } from "../api/types";
import { BaseMessage } from "./BaseMessage";
import { MentionText } from "./MentionText";

interface Actor { kind: "human" | "claude" | "codex" | "system"; initial: string; displayName: string }

export function ReviewMessage({ message, actor }: { message: MessageDTO; actor: Actor }) {
  const refId = (message.metadata as { ref_message_id?: number }).ref_message_id;
  return (
    <BaseMessage
      actor={actor}
      timeIso={message.created_at}
      tag="review"
      tone="review"
      body={
        <div>
          <MentionText>{message.body}</MentionText>
          {refId !== undefined && (
            <div className="text-[11px] font-mono text-text-dim mt-1">↳ #{refId}</div>
          )}
        </div>
      }
    />
  );
}
