import type { MessageDTO } from "../api/types";
import { BaseMessage } from "./BaseMessage";

interface Actor { kind: "human" | "claude" | "codex" | "system"; initial: string; displayName: string }

export function StatusMessage({ message, actor }: { message: MessageDTO; actor: Actor }) {
  return (
    <BaseMessage
      actor={actor}
      timeIso={message.created_at}
      tag="status"
      tone="status"
      body={<span className="font-mono text-[13px]">{message.body}</span>}
    />
  );
}
