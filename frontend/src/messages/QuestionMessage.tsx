import type { MessageDTO } from "../api/types";
import { BaseMessage } from "./BaseMessage";
import { MentionText } from "./MentionText";

interface Actor { kind: "human" | "claude" | "codex" | "system"; initial: string; displayName: string }

export function QuestionMessage({ message, actor }: { message: MessageDTO; actor: Actor }) {
  return (
    <BaseMessage
      msgId={message.id} actor={actor}
      timeIso={message.created_at}
      tag="question"
      tone="question"
      body={<MentionText>{message.body}</MentionText>}
    />
  );
}
