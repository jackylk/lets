export const MESSAGE_TYPES = [
  "chat", "status", "finding", "decision", "question",
  "handoff", "review", "artifact_revision", "spec_change",
  "nudge", "proactive_finding", "task_tree_proposal", "goal_proposal", "system",
] as const;
export type MessageType = (typeof MESSAGE_TYPES)[number];

export const ACTOR_TYPES = ["human", "agent", "system"] as const;
export type ActorType = (typeof ACTOR_TYPES)[number];

export interface MessageDTO {
  id: number;
  topic_id: number;
  type: MessageType;
  actor_type: ActorType;
  actor_id: number | null;
  body: string;
  metadata: Record<string, unknown>;
  ref_event_id: number | null;
  created_at: string;
}

export interface TopicDTO {
  id: number;
  slug: string;
  title: string;
  project_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface HumanDTO { id: number; name: string; }
export interface AgentInstanceDTO { id: number; role: string; device_label: string; }
export interface IdentityDTO { human: HumanDTO; agent_instance?: AgentInstanceDTO; }

export interface PostMessageInput {
  topic_id: number;
  type: MessageType;
  actor_type: ActorType;
  actor_id: number | null;
  body: string;
  metadata?: Record<string, unknown>;
  ref_event_id?: number | null;
  addressed_to?: string | null;
}

export interface ArtifactVersionDTO {
  id: number; artifact_id: number; version_label: string;
  backend_revision_id: string; summary: string | null;
  preview_uri: string | null; created_at: string;
}
export interface ArtifactDTO {
  id: number; slug: string; type: string; backend: string;
  backend_ref: string; title: string; topic_id: number;
  current_version_id: number | null; versions: ArtifactVersionDTO[];
}

export interface SpecChangeMeta {
  file: string; before: unknown; after: unknown; approvers?: string[];
}
export interface ArtifactRevisionMeta {
  artifact_id?: number; artifact_name?: string; version: string; preview_uri?: string;
}
export interface TaskTreeProposalMeta {
  title: string;
  items: Array<{ title: string; owner_name?: string; status?: "pending" | "active" | "done" }>;
}
export interface NudgeMeta { reason: string; target_actor_id?: number; }
export interface DecisionMeta { decision_type: "adopt" | "reject" | "defer"; ref_message_id?: number; }

export interface TokenRowDTO {
  id: number;
  label: string | null;
  human_id: number;
  agent_instance_id: number | null;
  agent_instance: { id: number; role: string; device_label: string } | null;
  created_at: string;
  last_used_at: string | null;
  revoked_at: string | null;
}

export interface CreateTokenInput {
  label: string;
  role: string;
  device_label: string;
}

export interface CreateTokenResponseDTO {
  id: number;
  value: string;
  label: string;
  agent_instance: { id: number; role: string; device_label: string };
}

export interface ProjectDTO {
  id: number;
  slug: string;
  name: string;
  description: string | null;
  owner_human_id: number | null;
  repo_path: string | null;
  created_at: string;
  updated_at: string;
}

export interface ParticipantsDTO {
  humans: Array<{ id: number; name: string; email: string | null }>;
  agents: Array<{ id: number; device_label: string; role: string; human_name: string }>;
}

export interface GitStatusDTO {
  head: {
    sha: string;
    short_sha: string;
    subject: string;
    author: string;
    date: string;
  };
  dirty: string[];
}

export interface OnlineAgentDTO {
  agent_instance_id: number;
  role: string;
  device_label: string;
  human_name: string;
  last_seen_at: string;
}

export interface AgentInstanceRowDTO {
  agent_instance_id: number;
  role: string;
  device_label: string;
  human_id: number;
  human_name: string;
  last_seen_at: string | null;
  is_online: number;  // 0 or 1 from SQLite
}

export interface AttentionMessageDTO extends MessageDTO {
  topic_slug: string;
  topic_title: string;
  project_id: number | null;
}

export interface AttentionDTO {
  needs_decision: AttentionMessageDTO[];
  mentioned_questions: AttentionMessageDTO[];
  suggestions: AttentionMessageDTO[];
}
