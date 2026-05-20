import { describe, it, expect } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../test/render";
import { TaskTreeProposalMessage } from "./TaskTreeProposalMessage";

const sampleMessage = {
  id: 6, topic_id: 1, type: "task_tree_proposal" as const,
  actor_type: "agent" as const, actor_id: 11,
  body: "建议分 3 个任务",
  metadata: {
    title: "PPT",
    items: [
      { title: "Framing", status: "done" },
      { title: "矩阵", status: "active" },
      { title: "排练", status: "pending" },
    ],
  },
  ref_event_id: null,
  created_at: "2026-05-19T09:33:00Z",
};

describe("<TaskTreeProposalMessage />", () => {
  it("renders title + items as before", () => {
    renderWithProviders(
      <TaskTreeProposalMessage
        actor={{ kind: "claude", initial: "CC", displayName: "claude" }}
        message={sampleMessage}
      />,
    );
    expect(screen.getByText("PPT")).toBeInTheDocument();
    expect(screen.getByText("Framing")).toBeInTheDocument();
  });

  it("renders Adopt button and calls the endpoint on click", async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <TaskTreeProposalMessage
        actor={{ kind: "claude", initial: "CC", displayName: "claude" }}
        message={sampleMessage}
      />,
    );
    const btn = screen.getByRole("button", { name: /Adopt as task tree/i });
    await user.click(btn);
    await waitFor(() => {
      expect(screen.getByText(/Adopted/i)).toBeInTheDocument();
    });
  });
});
