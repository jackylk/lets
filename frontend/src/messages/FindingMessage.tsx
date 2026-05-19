import type { MessageDTO } from "../api/types";
import { BaseMessage } from "./BaseMessage";
import { MentionText } from "./MentionText";

interface Actor { kind: "human" | "claude" | "codex" | "system"; initial: string; displayName: string }

export function FindingMessage({ message, actor }: { message: MessageDTO; actor: Actor }) {
  return (
    <BaseMessage
      actor={actor}
      timeIso={message.created_at}
      tag="finding"
      tone="finding"
      body={<MentionText>{message.body}</MentionText>}
    />
  );
}
