import type { MessageDTO } from "../api/types";

export interface DirectoryEntry {
  human?: { id: number; name: string };
  agentInstance?: { id: number; role: string; device_label: string };
}

export interface Directory {
  humans: { id: number; name: string }[];
  agentInstances: { id: number; role: string; device_label: string; human_id: number }[];
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
    const role = (a?.role ?? "agent") as "claude" | "codex";
    const kind = role === "claude" ? ("claude" as const) : ("codex" as const);
    const initial = role === "claude" ? "CC" : role === "codex" ? "CX" : "??";
    const display = a ? `${a.role} · ${a.device_label}` : `${role}#${m.actor_id}`;
    return { kind, initial, displayName: display };
  };
}
