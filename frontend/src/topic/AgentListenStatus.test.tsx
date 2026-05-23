import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { AgentListenStatus } from "./AgentListenStatus";
import type { MessageDTO, WorkspaceMember } from "../api/types";

function msg(over: Partial<MessageDTO>): MessageDTO {
  return {
    id: 0, topic_id: 1, type: "chat", actor_type: "human", actor_id: 1,
    body: "", metadata: {}, ref_event_id: null,
    created_at: new Date(Date.now() - 30_000).toISOString().replace("T", " ").replace("Z", ""),
    ...over,
  };
}

const codexMember: WorkspaceMember = {
  kind: "agent",
  id: 4,
  role: "codex",
  device_label: "neo-mbp",
  model: null,
  display_name: "Neo",
  owner_human_id: 1,
  owner_name: "Jacky Li",
  paused_at: null,
  deleted_at: null,
  joined_at: "2026-01-01T00:00:00Z",
  last_seen_at: "2026-01-01T00:00:00Z",
  is_online: 1,
};

describe("<AgentListenStatus />", () => {
  it("renders nothing before any agent activity", () => {
    const { container } = render(<AgentListenStatus messages={[
      msg({ id: 1, body: "first" }),
    ]} />);
    expect(container.querySelector("[data-testid=agent-listen-status]")).toBeNull();
  });

  it("shows 在听 + read cursor + unread count once the agent has replied", () => {
    const messages: MessageDTO[] = [
      msg({ id: 1, body: "ping" }),
      msg({ id: 2, type: "chat", actor_type: "agent", actor_id: 4, body: "pong",
            metadata: { cites: [1] } }),
      msg({ id: 3, body: "follow-up" }),
      msg({ id: 4, body: "another" }),
    ];
    render(<AgentListenStatus messages={messages} workspaceMembers={[codexMember]} />);
    expect(screen.getByText(/Neo 在听/)).toBeInTheDocument();
    expect(screen.getByText(/读到/)).toBeInTheDocument();
    expect(screen.getByText(/上次发言/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /2 未读/ })).toBeInTheDocument();
  });

  it("shows 思考中 when latest agent status is unfollowed by a reply", () => {
    const now = new Date();
    const t = (offsetSec: number) =>
      new Date(now.getTime() - offsetSec * 1000)
        .toISOString().replace("T", " ").replace("Z", "");
    const messages: MessageDTO[] = [
      msg({ id: 1, body: "ping me", created_at: t(20) }),
      msg({
        id: 2, type: "status", actor_type: "agent", actor_id: 4,
        body: "思考中…", metadata: { phase: "thinking", cites: [1] },
        created_at: t(8),
      }),
    ];
    render(<AgentListenStatus messages={messages} workspaceMembers={[codexMember]} />);
    expect(screen.getByText(/Neo 思考中/)).toBeInTheDocument();
    expect(screen.getByTestId("agent-listen-status")).toHaveAttribute("data-phase", "thinking");
  });

  it("shows 调用失败 when the latest agent result is an error finding", () => {
    const now = new Date();
    const t = (offsetSec: number) =>
      new Date(now.getTime() - offsetSec * 1000)
        .toISOString().replace("T", " ").replace("Z", "");
    const messages: MessageDTO[] = [
      msg({ id: 1, body: "ping", created_at: t(20) }),
      msg({
        id: 2, type: "status", actor_type: "agent", actor_id: 4,
        body: "思考中…", metadata: { phase: "thinking", cites: [1] },
        created_at: t(12),
      }),
      msg({
        id: 3, type: "finding", actor_type: "agent", actor_id: 4,
        body: "Claude CLI 调用失败。 · ERROR", metadata: { cites: [1] },
        created_at: t(8),
      }),
    ];
    render(<AgentListenStatus messages={messages} workspaceMembers={[codexMember]} />);
    expect(screen.getByText(/Neo 调用失败/)).toBeInTheDocument();
    expect(screen.getByTestId("agent-listen-status")).toHaveAttribute("data-phase", "failed");
  });


  it("shows 即将介入 with a countdown to the debounce-fire moment", () => {
    const now = new Date();
    const t = (offsetSec: number) =>
      new Date(now.getTime() - offsetSec * 1000)
        .toISOString().replace("T", " ").replace("Z", "");
    const messages: MessageDTO[] = [
      msg({
        id: 1, type: "chat", actor_type: "agent", actor_id: 4,
        body: "earlier reply", metadata: { cites: [0] }, created_at: t(600),
      }),
      // Human posted 2s ago, default debounce window is 6s → ~4s remaining.
      msg({ id: 2, body: "what about Y", created_at: t(2) }),
    ];
    render(<AgentListenStatus messages={messages} workspaceMembers={[codexMember]} />);
    expect(screen.getByText(/Neo 即将介入/)).toBeInTheDocument();
    expect(screen.getByTestId("agent-listen-status")).toHaveAttribute("data-phase", "impending");
    // Countdown should say "Xs 后" not "Xs"
    expect(screen.getByText(/[1-9]\d?s 后/)).toBeInTheDocument();
  });

  it("urgent (@-mention) message gets the shorter 2s debounce window", () => {
    const now = new Date();
    const t = (offsetSec: number) =>
      new Date(now.getTime() - offsetSec * 1000)
        .toISOString().replace("T", " ").replace("Z", "");
    const messages: MessageDTO[] = [
      msg({
        id: 1, type: "chat", actor_type: "agent", actor_id: 4,
        body: "earlier reply", metadata: { cites: [0] }, created_at: t(600),
      }),
      // "@" present → urgent. 0.5s after post → ~2s window means ~2s left.
      msg({ id: 2, body: "@cc 急", created_at: t(0.5) }),
    ];
    render(<AgentListenStatus messages={messages} workspaceMembers={[codexMember]} />);
    expect(screen.getByText(/Neo 即将介入/)).toBeInTheDocument();
    // Must show 2s or less (not the normal 6s).
    expect(screen.getByText(/^· [12]s 后$/)).toBeInTheDocument();
  });

  it("hides the unread jump when there are no unread messages", () => {
    const messages: MessageDTO[] = [
      msg({ id: 1, body: "ping" }),
      msg({ id: 2, type: "chat", actor_type: "agent", actor_id: 4, body: "pong",
            metadata: { cites: [1] } }),
    ];
    render(<AgentListenStatus messages={messages} />);
    expect(screen.queryByText(/未读/)).toBeNull();
  });
});
