import type { AgentInstanceRowDTO, WorkspaceMemberAgent } from "../api/types";

const MATRIX_NAMES = [
  "Neo",
  "Trinity",
  "Morpheus",
  "Oracle",
  "Tank",
  "Switch",
  "Apoc",
  "Seraph",
  "Niobe",
  "Dozer",
  "Link",
  "Sparks",
];

type AgentLike = Pick<AgentInstanceRowDTO, "agent_instance_id" | "display_name" | "role">;
type WorkspaceAgentLike = Pick<WorkspaceMemberAgent, "id" | "display_name" | "role">;
type AgentWithOwner =
  | (AgentLike & Pick<AgentInstanceRowDTO, "human_name">)
  | (WorkspaceAgentLike & Pick<WorkspaceMemberAgent, "owner_name">);

export function fallbackAgentName(id: number) {
  const base = MATRIX_NAMES[Math.abs(id - 1) % MATRIX_NAMES.length];
  const cycle = Math.floor(Math.abs(id - 1) / MATRIX_NAMES.length);
  return cycle === 0 ? base : `${base} ${cycle + 1}`;
}

function isGeneratedMatrixName(name: string) {
  return MATRIX_NAMES.some((base) => name === base || name.startsWith(`${base} `));
}

export function roleTitle(role: string) {
  if (role === "codex") return "Codex";
  if (role === "claude") return "Claude Code";
  if (role === "cc-deepseek") return "CC DeepSeek";
  if (role === "cc-doubao") return "CC Doubao";
  return role;
}

export function defaultModelForRole(role: string) {
  if (role === "claude") return "claude-opus-4-7";
  if (role === "codex") return "gpt-5.5";
  return null;
}

export function agentShortName(agent: AgentLike | WorkspaceAgentLike) {
  const id = "agent_instance_id" in agent ? agent.agent_instance_id : agent.id;
  return agent.display_name || fallbackAgentName(id) || `${agent.role}-${id}`;
}

export function agentDisplayName(agent: AgentWithOwner) {
  const ownerName = "owner_name" in agent ? agent.owner_name : agent.human_name;
  const displayName = agent.display_name?.trim();
  if (displayName && !isGeneratedMatrixName(displayName)) return displayName;
  return `${roleTitle(agent.role)} - ${ownerName}`;
}

export function agentStatusLabel(agent: Pick<AgentInstanceRowDTO, "deleted_at" | "paused_at" | "is_online">) {
  if (agent.deleted_at) return "已退役";
  if (agent.paused_at) return "已暂停";
  return agent.is_online === 1 ? "在线" : "离线";
}
