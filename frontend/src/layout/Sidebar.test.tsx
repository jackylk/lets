import { describe, it, expect, vi } from "vitest";
import { screen, fireEvent } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { Sidebar } from "./Sidebar";
import type { Workspace, TopicDTO, WorkspaceMember } from "../api/types";

const makeWorkspace = (id: number, name: string, slug: string): Workspace => ({
  id,
  name,
  slug,
  description: null,
  owner_human_id: 1,
  is_private: true,
  my_role: id === 1 ? "owner" : "member",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
});

const makeTopic = (id: number, slug: string, title: string): TopicDTO => ({
  id,
  slug,
  title,
  project_id: 1,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
});

const ws1 = makeWorkspace(1, "我的工作区", "my-ws");
const ws2 = makeWorkspace(2, "用户认证", "user-auth");

const defaultProps = {
  activeWorkspace: ws1,
  workspaces: [ws1, ws2],
  topics: [makeTopic(10, "topic-abc12", "新话题")],
  members: [] as WorkspaceMember[],
  activeTopicId: null,
  onSelectTopic: vi.fn(),
  onCreateTopic: vi.fn(),
  onSwitchWorkspace: vi.fn(),
  onCreateWorkspace: vi.fn(),
  onInviteMember: vi.fn(),
};

describe("<Sidebar />", () => {
  it("renders the active workspace's topics and collapses others", () => {
    renderWithProviders(<Sidebar {...defaultProps} />);
    // Active workspace switcher shows name
    expect(screen.getByText(/我的工作区/)).toBeInTheDocument();
    // Active workspace topics rendered
    expect(screen.getByText("新话题")).toBeInTheDocument();
    // Other workspace collapsed section visible (may appear in switcher chips AND section)
    expect(screen.getAllByText("用户认证").length).toBeGreaterThan(0);
  });

  it("shows the topic count in the topics section header", () => {
    renderWithProviders(<Sidebar {...defaultProps} />);
    // The topics section should show count "1"
    expect(screen.getByText("1")).toBeInTheDocument();
  });

  it("renders members section", () => {
    const members: WorkspaceMember[] = [
      {
        kind: "human",
        id: 1,
        name: "Neo",
        email: null,
        avatar_url: null,
        role: "owner",
        joined_at: "2026-01-01T00:00:00Z",
      },
    ];
    renderWithProviders(<Sidebar {...defaultProps} members={members} />);
    expect(screen.getByText("Neo")).toBeInTheDocument();
    expect(screen.getByText("owner")).toBeInTheDocument();
  });

  it("calls onSelectTopic when a topic row is clicked", () => {
    const onSelectTopic = vi.fn();
    renderWithProviders(<Sidebar {...defaultProps} onSelectTopic={onSelectTopic} />);
    fireEvent.click(screen.getByText("新话题"));
    expect(onSelectTopic).toHaveBeenCalledWith(10);
  });

  it("shows create-workspace inline form when + is clicked", () => {
    renderWithProviders(<Sidebar {...defaultProps} />);
    fireEvent.click(screen.getByRole("button", { name: "新建工作区" }));
    expect(screen.getByRole("textbox")).toBeInTheDocument();
  });

  it("shows settings link when onClickSettings is provided", () => {
    const onClickSettings = vi.fn();
    renderWithProviders(
      <Sidebar {...defaultProps} onClickSettings={onClickSettings} />,
    );
    expect(screen.getByText("设置")).toBeInTheDocument();
    fireEvent.click(screen.getByText("设置"));
    expect(onClickSettings).toHaveBeenCalledOnce();
  });

  it("does not render ChannelRow — only TopicRow style buttons", () => {
    renderWithProviders(<Sidebar {...defaultProps} />);
    // No old masthead / Let's branding (that was removed from sidebar)
    // The primary topic button should have TOPIC- (first 6 chars of 'topic-abc12')
    expect(screen.getByText("TOPIC-")).toBeInTheDocument();
  });
});
