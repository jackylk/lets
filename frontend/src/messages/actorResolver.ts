import type { MessageDTO } from "../api/types";
import { agentShortName } from "../agent/display";

export interface DirectoryEntry {
  human?: { id: number; name: string };
  agentInstance?: { id: number; role: string; device_label: string; display_name: string | null };
}

export interface Directory {
  humans: { id: number; name: string }[];
  agentInstances: { id: number; role: string; device_label: string; display_name: string | null; human_id: number }[];
}

function agentInitial(displayName: string) {
  return displayName.trim().slice(0, 1).toUpperCase() || "?";
}

export function makeActorResolver(dir: Directory) {
  return function resolve(m: MessageDTO) {
    if (m.actor_type === "system") {
      return { kind: "system" as const, initial: "S", displayName: "system" };
    }
    if (m.actor_type === "human") {
      const h = dir.humans.find((x) => x.id === m.actor_id);
      const name = h?.name ?? "?";
      return { kind: "human" as const, initial: name[0]?.toUpperCase() ?? "?", displayName: name };
    }
    const a = dir.agentInstances.find((x) => x.id === m.actor_id);
    const role = a?.role;
    const kind = role === "codex" ? ("codex" as const) : ("claude" as const);
    const display = a ? agentShortName(a) : `agent#${m.actor_id}`;
    const initial = a ? agentInitial(display) : "?";
    return { kind, initial, displayName: display };
  };
}
