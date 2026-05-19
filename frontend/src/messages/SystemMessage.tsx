import type { MessageDTO } from "../api/types";
import { formatHHMM } from "../lib/time";

interface Actor { kind: "human" | "claude" | "codex" | "system"; initial: string; displayName: string }

export function SystemMessage({ message }: { message: MessageDTO; actor: Actor }) {
  return (
    <div data-testid="message-row" className="py-1 px-3 text-center text-[12px] text-text-dim italic">
      <span>{message.body}</span>
      <span className="ml-2 font-mono text-[11px]">{formatHHMM(message.created_at)}</span>
    </div>
  );
}
