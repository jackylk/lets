import type { MessageDTO } from "../api/types";
import type { DecisionMeta } from "../api/types";
import { BaseMessage } from "./BaseMessage";

interface Actor { kind: "human" | "claude" | "codex" | "system"; initial: string; displayName: string }

export function DecisionMessage({ message, actor }: { message: MessageDTO; actor: Actor }) {
  const meta = message.metadata as Partial<DecisionMeta>;
  const decision = meta.decision_type ?? "adopt";
  return (
    <BaseMessage
      actor={actor}
      timeIso={message.created_at}
      tag={`decision · ${decision}`}
      tone="decision"
      body={
        <div>
          <span>{message.body}</span>
          {meta.ref_message_id !== undefined && (
            <span className="ml-2 text-[11px] font-mono text-text-dim">↳ #{meta.ref_message_id}</span>
          )}
        </div>
      }
    />
  );
}
