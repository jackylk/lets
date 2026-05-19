import type { MessageDTO, ArtifactRevisionMeta } from "../api/types";
import { BaseMessage } from "./BaseMessage";
import { SlideThumb } from "./SlideThumb";

interface Actor { kind: "human" | "claude" | "codex" | "system"; initial: string; displayName: string }

export function ArtifactRevisionMessage({ message, actor }: { message: MessageDTO; actor: Actor }) {
  const meta = message.metadata as Partial<ArtifactRevisionMeta>;
  const name = meta.artifact_name ?? `artifact#${meta.artifact_id ?? "?"}`;
  const version = meta.version ?? "?";
  return (
    <BaseMessage
      actor={actor}
      timeIso={message.created_at}
      tag={`artifact_revision · ${version}`}
      tone="artifact"
      body={
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <span className="font-mono text-[13px]">{name}</span>
            <span className="bg-artifact text-bg px-1.5 py-px rounded text-[10px] font-mono">{version}</span>
          </div>
          <div className="text-[13px]">{message.body}</div>
          <div className="flex gap-1.5">
            <SlideThumb num={1} variant="title" />
            <SlideThumb num={2} variant="text" />
            <SlideThumb num={3} variant="chart" />
            <SlideThumb num={4} variant="grid" />
          </div>
        </div>
      }
    />
  );
}
