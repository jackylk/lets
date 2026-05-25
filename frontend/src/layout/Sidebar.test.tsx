import { describe, it, expect, vi } from "vitest";
import { screen, fireEvent, waitFor } from "@testing-library/react";
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

const makeTopic = (
  id: number,
  slug: string,
  title: string,
  overrides: Partial<TopicDTO> = {},
): TopicDTO => ({
  id,
  slug,
  title,
  project_id: 1,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  ...overrides,
});

const ws1 = makeWorkspace(1, "我的工作区", "my-ws");
const ws2 = makeWorkspace(2, "用户认证", "user-auth");

const defaultProps = {
  activeWorkspace: ws1,
  workspaces: [ws1, ws2],
  topics: [makeTopic(10, "topic-abc12", "新话题")],
  allTopics: [makeTopic(10, "topic-abc12", "新话题")],
  archivedTopics: [] as TopicDTO[],
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
    expect(screen.getAllByText(/我的工作区/).length).toBeGreaterThan(0);
    // Active workspace topics rendered
    expect(screen.getByText("新话题")).toBeInTheDocument();
    // Other workspace collapsed section visible (may appear in switcher chips AND section)
    expect(screen.getAllByText("用户认证").length).toBeGreaterThan(0);
  });

  it("shows the topic count in the topics section header", () => {
    renderWithProviders(<Sidebar {...defaultProps} canViewAllTopics />);
    expect(screen.getByRole("button", { name: "我的 1" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "全部 1" })).toBeInTheDocument();
  });

  it("separates the public all-member topic from regular topics", () => {
    const publicTopic = makeTopic(9, "all-hands-1", "全员话题", { visibility: "public" });
    renderWithProviders(
      <Sidebar
        {...defaultProps}
        topics={[publicTopic, makeTopic(10, "topic-abc12", "新话题")]}
        allTopics={[publicTopic, makeTopic(10, "topic-abc12", "新话题")]}
        canViewAllTopics
      />,
    );

    expect(screen.getByText("全员")).toBeInTheDocument();
    expect(screen.getAllByText("全员话题")).toHaveLength(1);
    expect(screen.getByRole("button", { name: "我的 2" })).toBeInTheDocument();
  });

  it("does not offer archive or delete actions for the public all-member topic", () => {
    const publicTopic = makeTopic(9, "all-hands-1", "全员话题", { visibility: "public" });
    renderWithProviders(
      <Sidebar
        {...defaultProps}
        topics={[publicTopic, makeTopic(10, "topic-abc12", "新话题")]}
        allTopics={[publicTopic, makeTopic(10, "topic-abc12", "新话题")]}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "全员话题 话题操作" }));
    expect(screen.getByText("重命名")).toBeEnabled();
    expect(screen.queryByText("归档")).not.toBeInTheDocument();
    expect(screen.queryByText("删除")).not.toBeInTheDocument();
  });

  it("hides owner-only topic tabs and create action for guests", () => {
    renderWithProviders(<Sidebar {...defaultProps} isGuest canCreateTopic={false} />);

    expect(screen.getByText("话题")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "我的 1" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "全部 1" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "归档 0" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "新建话题" })).not.toBeInTheDocument();
    expect(screen.getByText("新话题")).toBeInTheDocument();
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
        last_seen_at: "2026-01-01T00:00:00Z",
        is_online: 1,
      },
    ];
    renderWithProviders(<Sidebar {...defaultProps} members={members} />);
    expect(screen.getByText("Neo")).toBeInTheDocument();
    expect(screen.getByText("owner")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "邀请工作区成员或 agent" })).toBeInTheDocument();
  });

  it("toggles the member section between current topic and workspace roster", async () => {
    const members: WorkspaceMember[] = [
      {
        kind: "human",
        id: 1,
        name: "Neo",
        email: null,
        avatar_url: null,
        role: "owner",
        joined_at: "2026-01-01T00:00:00Z",
        last_seen_at: "2026-01-01T00:00:00Z",
        is_online: 1,
      },
      {
        kind: "human",
        id: 99,
        name: "Outside Member",
        email: null,
        avatar_url: null,
        role: "member",
        joined_at: "2026-01-01T00:00:00Z",
        last_seen_at: null,
        is_online: 0,
      },
    ];
    renderWithProviders(
      <Sidebar
        {...defaultProps}
        topics={[makeTopic(1, "t-ppt", "为 Agent 记忆写一个研讨 PPT")]}
        allTopics={[makeTopic(1, "t-ppt", "为 Agent 记忆写一个研讨 PPT")]}
        activeTopicId={1}
        members={members}
      />,
    );

    expect(await screen.findByText("当前话题成员")).toBeInTheDocument();
    expect(screen.queryByText("Outside Member")).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "看工作区全部" }));

    expect(screen.getByText("当前工作区成员")).toBeInTheDocument();
    expect(screen.getByText("Outside Member")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "看当前话题" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "邀请工作区成员或 agent" })).toBeInTheDocument();
  });

  it("offers a topic-scoped invite action from the current topic member section", async () => {
    const onInviteTopicMember = vi.fn();
    renderWithProviders(
      <Sidebar
        {...defaultProps}
        topics={[makeTopic(1, "t-ppt", "为 Agent 记忆写一个研讨 PPT")]}
        allTopics={[makeTopic(1, "t-ppt", "为 Agent 记忆写一个研讨 PPT")]}
        activeTopicId={1}
        canManageMembers
        onInviteTopicMember={onInviteTopicMember}
      />,
    );

    await screen.findByText("当前话题成员");
    fireEvent.click(screen.getByRole("button", { name: "邀请同事到此话题" }));
    fireEvent.click(screen.getByText("邀请同事到此话题"));

    expect(onInviteTopicMember).toHaveBeenCalledOnce();
  });

  it("calls invite handlers from the members section add menu", () => {
    const onInviteMember = vi.fn();
    const onInviteAgent = vi.fn();
    renderWithProviders(
      <Sidebar
        {...defaultProps}
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

  it("calls onSelectTopic when a topic row is clicked", () => {
    const onSelectTopic = vi.fn();
    renderWithProviders(<Sidebar {...defaultProps} onSelectTopic={onSelectTopic} />);
    fireEvent.click(screen.getByText("新话题"));
    expect(onSelectTopic).toHaveBeenCalledWith(10);
  });

  it("renders only enabled topic menu actions", () => {
    renderWithProviders(<Sidebar {...defaultProps} />);
    fireEvent.click(screen.getByRole("button", { name: "新话题 话题操作" }));

    expect(screen.getByText("重命名")).toBeEnabled();
    expect(screen.getByText("归档")).toBeEnabled();
    expect(screen.getByText("删除")).toBeEnabled();
    expect(screen.queryByText("复制链接")).not.toBeInTheDocument();
    expect(screen.queryByText("静音")).not.toBeInTheDocument();
  });

  it("calls archive and delete handlers from the topic menu", () => {
    const onArchiveTopic = vi.fn();
    const onDeleteTopic = vi.fn();
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);

    renderWithProviders(
      <Sidebar
        {...defaultProps}
        onArchiveTopic={onArchiveTopic}
        onDeleteTopic={onDeleteTopic}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "新话题 话题操作" }));
    fireEvent.click(screen.getByText("归档"));
    expect(onArchiveTopic).toHaveBeenCalledWith(10);

    fireEvent.click(screen.getByRole("button", { name: "新话题 话题操作" }));
    fireEvent.click(screen.getByText("删除"));
    expect(confirm).toHaveBeenCalled();
    expect(onDeleteTopic).toHaveBeenCalledWith(10);

    confirm.mockRestore();
  });

  it("shows archived topics and calls restore from the topic menu", async () => {
    const onRestoreTopic = vi.fn();
    renderWithProviders(
      <Sidebar
        {...defaultProps}
        archivedTopics={[makeTopic(11, "old-one", "旧话题")]}
        onRestoreTopic={onRestoreTopic}
      />,
    );

    fireEvent.click(screen.getByText("归档 1"));
    expect(screen.getByText("旧话题")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "旧话题 话题操作" }));
    fireEvent.click(screen.getByText("恢复"));
    await waitFor(() => expect(onRestoreTopic).toHaveBeenCalledWith(11));
  });

  it("shows create-workspace inline form from the workspace menu", () => {
    renderWithProviders(<Sidebar {...defaultProps} />);
    fireEvent.click(screen.getByRole("button", { name: /我的工作区/ }));
    fireEvent.click(screen.getByText("新建工作区"));
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
    // Topic rows should prioritize the title, without the old slug prefix.
    expect(screen.getByRole("button", { name: "新话题" })).toBeInTheDocument();
    expect(screen.queryByText("TOPIC-")).not.toBeInTheDocument();
  });
});
