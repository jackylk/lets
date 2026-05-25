import type { ParticipantsDTO, TopicDTO, WorkspaceMember } from "../api/types";

const FALLBACK_JOINED_AT = "1970-01-01T00:00:00Z";

export function topicMembersFromParticipants(
  workspaceMembers: WorkspaceMember[],
  participants?: ParticipantsDTO,
  topic?: Pick<TopicDTO, "visibility"> | null,
): WorkspaceMember[] {
  if (participants?.is_public || topic?.visibility === "public") {
    return workspaceMembers;
  }
  if (!participants) return [];

  const participantHumanIds = new Set(participants.humans.map((h) => h.id));
  const participantAgentIds = new Set(participants.agents.map((a) => a.id));
  const included = new Set<string>();

  const out = workspaceMembers.filter((member) => {
    const keep =
      member.kind === "human"
        ? participantHumanIds.has(member.id)
        : participantAgentIds.has(member.id);
    if (keep) included.add(`${member.kind}:${member.id}`);
    return keep;
  });

  for (const human of participants.humans) {
    const key = `human:${human.id}`;
    if (included.has(key)) continue;
    out.push({
      kind: "human",
      id: human.id,
      name: human.name,
      email: human.email,
      avatar_url: null,
      role: human.role ?? "member",
      joined_at: human.created_at ?? FALLBACK_JOINED_AT,
      last_seen_at: null,
      is_online: 0,
    });
  }

  for (const agent of participants.agents) {
    const key = `agent:${agent.id}`;
    if (included.has(key)) continue;
    out.push({
      kind: "agent",
      id: agent.id,
      role: agent.role,
      device_label: agent.device_label,
      model: null,
      display_name: agent.display_name,
      owner_human_id: 0,
      owner_name: agent.human_name,
      paused_at: null,
      deleted_at: null,
      joined_at: agent.created_at ?? FALLBACK_JOINED_AT,
      last_seen_at: null,
      is_online: 0,
    });
  }

  return out;
}
