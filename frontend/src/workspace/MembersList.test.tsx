import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
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
};

const regularMember: WorkspaceMember = {
  kind: "human",
  id: 2,
  name: "Trinity",
  email: null,
  avatar_url: null,
  role: "member",
  joined_at: "2026-01-01T00:00:00Z",
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
};

describe("<MembersList />", () => {
  it("renders owner badge for human with owner role", () => {
    render(<MembersList members={[ownerMember]} onInvite={vi.fn()} />);
    expect(screen.getByText("Neo")).toBeInTheDocument();
    expect(screen.getByText("owner")).toBeInTheDocument();
  });

  it("does not render owner badge for non-owner human", () => {
    render(<MembersList members={[regularMember]} onInvite={vi.fn()} />);
    expect(screen.getByText("Trinity")).toBeInTheDocument();
    expect(screen.queryByText("owner")).toBeNull();
  });

  it("renders agent caption with owner_name", () => {
    render(<MembersList members={[agentMember]} onInvite={vi.fn()} />);
    expect(screen.getByText("Link")).toBeInTheDocument();
    expect(screen.getByText(/agent · Neo/)).toBeInTheDocument();
  });

  it("calls onInvite when invite button is clicked", () => {
    const onInvite = vi.fn();
    render(<MembersList members={[]} onInvite={onInvite} />);
    fireEvent.click(screen.getByText(/邀请人加入这个工作区/));
    expect(onInvite).toHaveBeenCalledOnce();
  });

  it("renders mixed humans and agents in order", () => {
    render(
      <MembersList members={[ownerMember, agentMember]} onInvite={vi.fn()} />,
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
        onInvite={vi.fn()}
      />,
    );
    expect(screen.getByText("Link · Neo")).toBeInTheDocument();
    expect(screen.getByText("Link · Trinity")).toBeInTheDocument();
  });

  it("renders 邀请 agent button only when onInviteAgent is provided", () => {
    const { rerender } = render(
      <MembersList members={[]} onInvite={vi.fn()} />,
    );
    expect(screen.queryByText(/邀请 agent/)).toBeNull();

    const onInviteAgent = vi.fn();
    rerender(
      <MembersList
        members={[]}
        onInvite={vi.fn()}
        onInviteAgent={onInviteAgent}
      />,
    );
    fireEvent.click(screen.getByText(/邀请 agent/));
    expect(onInviteAgent).toHaveBeenCalledOnce();
  });
});
