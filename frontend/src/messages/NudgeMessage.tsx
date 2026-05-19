import type { MessageDTO } from "../api/types";
import { BaseMessage } from "./BaseMessage";

interface Actor { kind: "system" | "human" | "claude" | "codex"; initial: string; displayName: string }

export function NudgeMessage({ message, actor }: { message: MessageDTO; actor: Actor }) {
  const meta = message.metadata as { reason?: string };
  return (
    <BaseMessage
      actor={actor}
      timeIso={message.created_at}
      tag={`nudge${meta.reason ? ` · ${meta.reason}` : ""}`}
      tone="nudge"
      body={<span>{message.body}</span>}
    />
  );
}
