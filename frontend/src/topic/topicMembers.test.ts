import { describe, expect, it } from "vitest";
import type { ParticipantsDTO, WorkspaceMember } from "../api/types";
import { topicMembersFromParticipants } from "./topicMembers";

const ownerMember: WorkspaceMember = {
  kind: "human",
  id: 1,
  name: "Neo",
  email: null,
  avatar_url: null,
  role: "owner",
  joined_at: "2026-01-01T00:00:00Z",
  last_seen_at: "2026-01-01T00:00:00Z",
  is_online: 1,
};

const regularMember: WorkspaceMember = {
  kind: "human",
  id: 2,
  name: "Trinity",
  email: null,
  avatar_url: null,
  role: "member",
  joined_at: "2026-01-01T00:00:00Z",
  last_seen_at: null,
  is_online: 0,
};

const agentMember: WorkspaceMember = {
  kind: "agent",
  id: 11,
  role: "claude",
  device_label: "neo-mbp",
  model: null,
  display_name: "Neo",
  owner_human_id: 1,
  owner_name: "Neo",
  paused_at: null,
  deleted_at: null,
  joined_at: "2026-01-01T00:00:00Z",
  last_seen_at: null,
  is_online: 0,
};

describe("topicMembersFromParticipants", () => {
  it("returns all workspace members for public topics", () => {
    const members = [ownerMember, regularMember, agentMember];
    expect(topicMembersFromParticipants(members, undefined, { visibility: "public" })).toEqual(members);
  });

  it("filters private topics to explicit participants", () => {
    const participants: ParticipantsDTO = {
      is_public: false,
      humans: [{ id: 2, name: "Trinity", email: null }],
      agents: [{
        id: 11,
        role: "claude",
        device_label: "neo-mbp",
        display_name: "Neo",
        model: "claude-opus-4-7",
        human_name: "Neo",
      }],
    };
    expect(
      topicMembersFromParticipants([ownerMember, regularMember, agentMember], participants, { visibility: "private" })
        .map((m) => `${m.kind}:${m.id}`),
    ).toEqual(["human:2", "agent:11"]);
  });

  it("excludes historical agent speakers from current topic members", () => {
    const participants: ParticipantsDTO = {
      is_public: false,
      humans: [],
      agents: [{
        id: 11,
        role: "claude",
        device_label: "neo-mbp",
        display_name: "Neo",
        model: null,
        human_name: "Neo",
        is_explicit: false,
      }],
    };

    expect(topicMembersFromParticipants([agentMember], participants, { visibility: "private" })).toEqual([]);
  });

  it("excludes historical human speakers from current topic members", () => {
    const participants: ParticipantsDTO = {
      is_public: false,
      humans: [{ id: 2, name: "Trinity", email: null, is_explicit: false }],
      agents: [],
    };

    expect(topicMembersFromParticipants([regularMember], participants, { visibility: "private" })).toEqual([]);
  });

  it("preserves agent model from participant fallback rows", () => {
    const participants: ParticipantsDTO = {
      is_public: false,
      humans: [],
      agents: [{
        id: 12,
        role: "codex",
        device_label: "neo-mbp",
        display_name: "Morpheus",
        model: "gpt-5-codex",
        human_name: "Neo",
      }],
    };

    const [agent] = topicMembersFromParticipants([], participants, { visibility: "private" });
    expect(agent).toMatchObject({
      kind: "agent",
      id: 12,
      model: "gpt-5-codex",
    });
  });
});
