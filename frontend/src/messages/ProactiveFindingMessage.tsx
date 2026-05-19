import type { MessageDTO } from "../api/types";
import { BaseMessage } from "./BaseMessage";
import { MentionText } from "./MentionText";

interface Actor { kind: "human" | "claude" | "codex" | "system"; initial: string; displayName: string }

export function ProactiveFindingMessage({ message, actor }: { message: MessageDTO; actor: Actor }) {
  return (
    <BaseMessage
      actor={actor}
      timeIso={message.created_at}
      tag="proactive"
      tone="proactive"
      body={<MentionText>{message.body}</MentionText>}
    />
  );
}
