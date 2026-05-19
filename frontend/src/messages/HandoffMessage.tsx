import type { MessageDTO } from "../api/types";
import { BaseMessage } from "./BaseMessage";
import { MentionText } from "./MentionText";

interface Actor { kind: "human" | "claude" | "codex" | "system"; initial: string; displayName: string }

export function HandoffMessage({ message, actor }: { message: MessageDTO; actor: Actor }) {
  const meta = message.metadata as { from_actor_id?: number; to_actor_id?: number };
  return (
    <BaseMessage
      actor={actor}
      timeIso={message.created_at}
      tag={`handoff · #${meta.from_actor_id ?? "?"} → #${meta.to_actor_id ?? "?"}`}
      tone="handoff"
      body={<MentionText>{message.body}</MentionText>}
    />
  );
}
