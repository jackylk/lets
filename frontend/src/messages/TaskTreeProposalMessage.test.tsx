import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { TaskTreeProposalMessage } from "./TaskTreeProposalMessage";

describe("<TaskTreeProposalMessage />", () => {
  it("renders task tree title + items", () => {
    renderWithProviders(
      <TaskTreeProposalMessage
        actor={{ kind: "claude", initial: "CC", displayName: "claude" }}
        message={{
          id: 6, topic_id: 1, type: "task_tree_proposal", actor_type: "agent", actor_id: 11,
          body: "建议分 3 个任务",
          metadata: {
            title: "PPT",
            items: [
              { title: "Framing", status: "done" },
              { title: "矩阵", status: "active" },
              { title: "排练", status: "pending" },
            ],
          },
          ref_event_id: null, created_at: "2026-05-19T09:33:00Z",
        }}
      />,
    );
    expect(screen.getByText("PPT")).toBeInTheDocument();
    expect(screen.getByText("Framing")).toBeInTheDocument();
    expect(screen.getByText(/1 \/ 3/)).toBeInTheDocument();
  });
});
