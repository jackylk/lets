import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MembersList } from "./MembersList";
import type { WorkspaceMember } from "../api/types";

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
  display_name: null,
  owner_human_id: 1,
  owner_name: "Neo",
  paused_at: null,
  deleted_at: null,
  joined_at: "2026-01-01T00:00:00Z",
  last_seen_at: "2026-01-01T00:00:00Z",
  is_online: 1,
};

describe("<MembersList />", () => {
  it("renders owner badge for human with owner role", () => {
    render(<MembersList members={[ownerMember]} />);
    expect(screen.getByText("Neo")).toBeInTheDocument();
    expect(screen.getByText("owner")).toBeInTheDocument();
  });

  it("does not render owner badge for non-owner human", () => {
    render(<MembersList members={[regularMember]} />);
    expect(screen.getByText("Trinity")).toBeInTheDocument();
    expect(screen.queryByText("owner")).toBeNull();
  });

  it("renders agent caption with owner_name", () => {
    render(<MembersList members={[agentMember]} />);
    expect(screen.getByText("Link")).toBeInTheDocument();
    expect(screen.getByText(/Claude Code/)).toBeInTheDocument();
    expect(screen.getByText("在线")).toBeInTheDocument();
    expect(screen.getByLabelText("Link 在线")).toBeInTheDocument();
  });

  it("does not duplicate workspace invite actions in the members section", () => {
    render(<MembersList members={[]} />);
    expect(screen.queryByText(/邀请人加入这个工作区/)).toBeNull();
    expect(screen.queryByText(/邀请 agent 加入这个工作区/)).toBeNull();
  });

  it("renders mixed humans and agents in order", () => {
    render(
      <MembersList members={[ownerMember, agentMember]} />,
    );
    expect(screen.getByText("Neo")).toBeInTheDocument();
    expect(screen.getByText("Link")).toBeInTheDocument();
  });

  it("adds owner name when two agents have the same display name", () => {
    const secondAgent: WorkspaceMember = {
      ...agentMember,
      id: 23,
      display_name: "Link",
      owner_human_id: 2,
      owner_name: "Trinity",
    };
    render(
      <MembersList
        members={[{ ...agentMember, display_name: "Link" }, secondAgent]}
      />,
    );
    expect(screen.getByText("Link · Neo")).toBeInTheDocument();
    expect(screen.getByText("Link · Trinity")).toBeInTheDocument();
  });

  it("keeps invite actions out of the members section", () => {
    render(<MembersList members={[]} />);
    expect(screen.queryByText(/邀请人/)).toBeNull();
    expect(screen.queryByText(/邀请 agent/)).toBeNull();
  });
});
