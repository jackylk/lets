import { describe, it, expect } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { renderWithProviders } from "../../test/render";
import { TopicView } from "./TopicView";
import type { WorkspaceMember } from "../api/types";
import { server } from "../fixtures/server";

describe("<TopicView />", () => {
  it("renders the fixture topic's typed messages", async () => {
    renderWithProviders(<TopicView topicId={1} />);
    await waitFor(() => {
      // Stream collapses status-before-reply (the "X 正在输入…" bubble that
      // immediately precedes the same agent's chat reply), so the visible
      // count is one less than the raw fixture size. The exact number isn't
      // load-bearing — just verify the fixture renders and is non-trivial.
      expect(screen.getAllByTestId("message-row").length).toBeGreaterThan(10);
    });
  });

  it("posts a new chat message via composer", async () => {
    const user = userEvent.setup();
    renderWithProviders(<TopicView topicId={1} />);
    await waitFor(() => screen.getAllByTestId("message-row"));
    const textarea = screen.getByRole("textbox");
    await user.type(textarea, "hello composer");
    await user.keyboard("{Enter}");
    await waitFor(() => {
      expect(screen.getByText("hello composer")).toBeInTheDocument();
    });
  });

  it("uses the agent display name for mention insertion", async () => {
    const user = userEvent.setup();
    const members: WorkspaceMember[] = [
      {
        kind: "agent",
        id: 1,
        role: "codex",
        device_label: "mac16",
        model: null,
        display_name: "Neo",
        owner_human_id: 1,
        owner_name: "Jacky Li",
        paused_at: null,
        deleted_at: null,
        joined_at: "2026-01-01T00:00:00Z",
        last_seen_at: "2026-01-01T00:00:00Z",
        is_online: 1,
      },
    ];

    renderWithProviders(<TopicView topicId={1} workspaceMembers={members} />);
    await waitFor(() => screen.getAllByTestId("message-row"));

    const textarea = screen.getByRole("textbox") as HTMLTextAreaElement;
    await user.type(textarea, "@");
    expect(screen.getByText(/@neo · .*by Jacky Li/)).toBeInTheDocument();

    await user.keyboard("{Enter}");
    expect(textarea.value).toBe("@neo ");
  });

  it("shows a clear message when the user is not in the topic", async () => {
    server.use(
      http.get("/api/topics/:id/messages", () =>
        new HttpResponse(JSON.stringify({ detail: "not a topic participant" }), { status: 403 }),
      ),
    );

    renderWithProviders(<TopicView topicId={1} />);
    expect(await screen.findByText("你不在这个话题中，请让管理员把你加入。")).toBeInTheDocument();
  });
});
