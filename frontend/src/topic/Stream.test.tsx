import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { Stream } from "./Stream";
import { StreamProvider } from "../messages/StreamContext";
import type { MessageDTO } from "../api/types";
import type { Directory } from "../messages/actorResolver";

// Stream now relies on its caller to install StreamProvider. Tests wrap.
function renderStream(messages: MessageDTO[], topicId: number) {
  return renderWithProviders(
    <StreamProvider messages={messages} directory={directory} topicId={topicId}>
      <Stream messages={messages} directory={directory} topicId={topicId} />
    </StreamProvider>,
  );
}

const directory: Directory = {
  humans: [{ id: 1, name: "Jacky" }],
  agentInstances: [{ id: 4, role: "claude", device_label: "mac16", human_id: 1 }],
};

function msg(over: Partial<MessageDTO>): MessageDTO {
  return {
    id: 0,
    topic_id: 1,
    type: "chat",
    actor_type: "human",
    actor_id: 1,
    body: "",
    metadata: {},
    ref_event_id: null,
    created_at: "2026-05-20 11:00:00",
    ...over,
  };
}

describe("<Stream />", () => {
  it("hides agent 'typing…' status once the same agent posted a real reply", () => {
    // Pre-set view mode = full so the agent's chat body is rendered
    // (default 'collapsed' would fold it into a one-liner summary).
    localStorage.setItem("lets:view-mode:topic:1", "full");
    const messages: MessageDTO[] = [
      msg({ id: 1, type: "chat", actor_type: "human", actor_id: 1, body: "@cc 在吗" }),
      msg({ id: 2, type: "status", actor_type: "agent", actor_id: 4, body: "claude 正在输入…" }),
      msg({ id: 3, type: "chat", actor_type: "agent", actor_id: 4, body: "在的，刚刚卡了一下" }),
    ];
    renderStream(messages, 1);
    expect(screen.queryByText(/正在输入/)).toBeNull();
    expect(screen.getByText(/在的，刚刚卡了一下/)).toBeInTheDocument();
    localStorage.removeItem("lets:view-mode:topic:1");
  });

  it("keeps the status visible while the agent's reply has not arrived yet", () => {
    const messages: MessageDTO[] = [
      msg({ id: 1, type: "chat", actor_type: "human", actor_id: 1, body: "@cc 在吗" }),
      msg({ id: 2, type: "status", actor_type: "agent", actor_id: 4, body: "claude 正在输入…" }),
    ];
    renderStream(messages, 1);
    expect(screen.getByText(/正在输入/)).toBeInTheDocument();
  });

  it("renders the read cursor + unread badge using metadata.cites", () => {
    const messages: MessageDTO[] = [
      msg({ id: 1, type: "chat", actor_type: "human", actor_id: 1, body: "first" }),
      msg({ id: 2, type: "chat", actor_type: "agent", actor_id: 4, body: "reply",
            metadata: { cites: [1] } }),
      // Human posts more after agent read up to #1 → these should be "unread"
      msg({ id: 3, type: "chat", actor_type: "human", actor_id: 1, body: "follow-up #3" }),
      msg({ id: 4, type: "chat", actor_type: "human", actor_id: 1, body: "follow-up #4" }),
    ];
    renderStream(messages, 1);
    expect(screen.getByText(/CC 已读到此处/)).toBeInTheDocument();
    // Two human messages after the cursor should be marked unread.
    expect(screen.getAllByText("未读").length).toBe(2);
  });

  it("default 'collapsed' mode folds agent chat into a one-line summary", () => {
    const messages: MessageDTO[] = [
      msg({ id: 1, type: "chat", actor_type: "human", actor_id: 1, body: "ping" }),
      msg({ id: 2, type: "chat", actor_type: "agent", actor_id: 4,
            body: "very long agent reply that should be folded",
            metadata: { cites: [1], headline: "提出三点挑战" } }),
    ];
    renderStream(messages, 42);
    // Headline visible; body NOT visible.
    expect(screen.getByText("提出三点挑战")).toBeInTheDocument();
    expect(screen.queryByText(/very long agent reply/)).toBeNull();
    // "展开" affordance on the collapsed row.
    expect(screen.getByText("展开")).toBeInTheDocument();
  });

  it("'humans-only' mode hides agent chats with an N-elision marker", () => {
    localStorage.setItem("lets:view-mode:topic:43", "humans-only");
    const messages: MessageDTO[] = [
      msg({ id: 1, type: "chat", actor_type: "human", actor_id: 1, body: "h1" }),
      msg({ id: 2, type: "chat", actor_type: "agent", actor_id: 4, body: "a1" }),
      msg({ id: 3, type: "chat", actor_type: "agent", actor_id: 4, body: "a2" }),
      msg({ id: 4, type: "chat", actor_type: "human", actor_id: 1, body: "h2" }),
    ];
    renderStream(messages, 43);
    expect(screen.getByText(/CC 中间说了 2 条/)).toBeInTheDocument();
    expect(screen.queryByText("a1")).toBeNull();
    expect(screen.queryByText("a2")).toBeNull();
    expect(screen.getByText("h1")).toBeInTheDocument();
    expect(screen.getByText("h2")).toBeInTheDocument();
    localStorage.removeItem("lets:view-mode:topic:43");
  });

  it("does not render a cursor when no agent reply has cites yet", () => {
    const messages: MessageDTO[] = [
      msg({ id: 1, type: "chat", actor_type: "human", actor_id: 1, body: "hi" }),
      msg({ id: 2, type: "chat", actor_type: "human", actor_id: 1, body: "still typing" }),
    ];
    renderStream(messages, 1);
    expect(screen.queryByText(/已读到此处/)).toBeNull();
    expect(screen.queryByText("未读")).toBeNull();
  });
});
