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
    expect(screen.getByText(/默认模型/)).toBeInTheDocument();
    expect(screen.getByText("在线")).toBeInTheDocument();
    expect(screen.getByLabelText("Link 在线")).toBeInTheDocument();
  });

  it("renders agent model in the status caption", () => {
    render(<MembersList members={[{ ...agentMember, model: "gpt-5-codex" }]} />);
    expect(screen.getByText(/gpt-5-codex/)).toBeInTheDocument();
    expect(screen.getByText("在线")).toBeInTheDocument();
  });

  it("renders mixed humans and agents in order", () => {
    render(
      <MembersList members={[ownerMember, agentMember]} />,
    );
    expect(screen.getByText("1 人 · 1 agent")).toBeInTheDocument();
    expect(screen.getByText("Neo")).toBeInTheDocument();
    expect(screen.getByText("Link")).toBeInTheDocument();
  });

  it("keeps the workspace name out of the members summary", () => {
    render(<MembersList members={[ownerMember, agentMember]} />);
    expect(screen.getByText("当前工作区成员")).toBeInTheDocument();
    expect(screen.queryByText(/我的工作区/)).toBeNull();
  });

  it("keeps agent owner name out of the compact status caption", () => {
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
    expect(screen.getAllByText("Link")).toHaveLength(2);
    expect(screen.queryByText(/Neo 管理/)).toBeNull();
    expect(screen.queryByText(/Trinity 管理/)).toBeNull();
  });

  it("opens invite actions from the members header", () => {
    const onInviteMember = vi.fn();
    const onInviteAgent = vi.fn();
    render(
      <MembersList
        members={[]}
        onInviteMember={onInviteMember}
        onInviteAgent={onInviteAgent}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "邀请工作区成员或 agent" }));
    fireEvent.click(screen.getByText("邀请成员"));
    expect(onInviteMember).toHaveBeenCalledOnce();

    fireEvent.click(screen.getByRole("button", { name: "邀请工作区成员或 agent" }));
    fireEvent.click(screen.getByText("邀请 agent"));
    expect(onInviteAgent).toHaveBeenCalledOnce();
  });
});
