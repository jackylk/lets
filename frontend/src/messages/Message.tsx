import type { MessageDTO } from "../api/types";
import { ChatMessage } from "./ChatMessage";
import { StatusMessage } from "./StatusMessage";
import { FindingMessage } from "./FindingMessage";
import { DecisionMessage } from "./DecisionMessage";
import { QuestionMessage } from "./QuestionMessage";
import { HandoffMessage } from "./HandoffMessage";
import { ReviewMessage } from "./ReviewMessage";
import { ArtifactRevisionMessage } from "./ArtifactRevisionMessage";
import { SpecChangeMessage } from "./SpecChangeMessage";
import { NudgeMessage } from "./NudgeMessage";
import { ProactiveFindingMessage } from "./ProactiveFindingMessage";
import { TaskTreeProposalMessage } from "./TaskTreeProposalMessage";
import { SystemMessage } from "./SystemMessage";

export interface ActorResolver {
  resolve(message: MessageDTO): {
    kind: "human" | "claude" | "codex" | "system";
    initial: string;
    displayName: string;
  };
}

interface Props {
  message: MessageDTO;
  resolveActor: ActorResolver["resolve"];
}

export function Message({ message, resolveActor }: Props) {
  const actor = resolveActor(message);
  switch (message.type) {
    case "chat":               return <ChatMessage message={message} actor={actor} />;
    case "status":             return <StatusMessage message={message} actor={actor} />;
    case "finding":            return <FindingMessage message={message} actor={actor} />;
    case "decision":           return <DecisionMessage message={message} actor={actor} />;
    case "question":           return <QuestionMessage message={message} actor={actor} />;
    case "handoff":            return <HandoffMessage message={message} actor={actor} />;
    case "review":             return <ReviewMessage message={message} actor={actor} />;
    case "artifact_revision":  return <ArtifactRevisionMessage message={message} actor={actor} />;
    case "spec_change":        return <SpecChangeMessage message={message} actor={actor} />;
    case "nudge":              return <NudgeMessage message={message} actor={actor} />;
    case "proactive_finding":  return <ProactiveFindingMessage message={message} actor={actor} />;
    case "task_tree_proposal": return <TaskTreeProposalMessage message={message} actor={actor} />;
    case "system":             return <SystemMessage message={message} actor={actor} />;
  }
}
