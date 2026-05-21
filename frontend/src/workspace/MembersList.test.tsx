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
  started_by_name: "Neo",
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

  it("renders agent caption with started_by_name", () => {
    render(<MembersList members={[agentMember]} onInvite={vi.fn()} />);
    expect(screen.getByText("claude")).toBeInTheDocument();
    expect(screen.getByText(/agent · Neo 启动/)).toBeInTheDocument();
  });

  it("calls onInvite when invite button is clicked", () => {
    const onInvite = vi.fn();
    render(<MembersList members={[]} onInvite={onInvite} />);
    fireEvent.click(screen.getByText(/邀请成员/));
    expect(onInvite).toHaveBeenCalledOnce();
  });

  it("renders mixed humans and agents in order", () => {
    render(
      <MembersList members={[ownerMember, agentMember]} onInvite={vi.fn()} />,
    );
    expect(screen.getByText("Neo")).toBeInTheDocument();
    expect(screen.getByText("claude")).toBeInTheDocument();
  });
});
