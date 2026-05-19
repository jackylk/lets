import { Avatar } from "../messages/Avatar";

interface P { kind: "human" | "claude" | "codex" | "system"; initial: string; name: string }
export function ParticipantsPanel({ participants }: { participants: P[] }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {participants.map((p) => (
        <div key={p.name} title={p.name}>
          <Avatar kind={p.kind} initial={p.initial} size="sm" />
        </div>
      ))}
    </div>
  );
}
