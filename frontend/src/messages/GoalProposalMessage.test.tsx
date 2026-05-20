import { describe, it, expect } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../test/render";
import { GoalProposalMessage } from "./GoalProposalMessage";

const sample = {
  id: 100, topic_id: 1, type: "goal_proposal" as const,
  actor_type: "agent" as const, actor_id: 11,
  body: "30 分钟 talk · 技术受众",
  metadata: { artifact_id: null, spec_text: "30 分钟 talk · 技术受众" },
  ref_event_id: null,
  created_at: "2026-05-19T09:30:00Z",
};

describe("<GoalProposalMessage />", () => {
  it("renders the proposed spec and an adopt button", () => {
    renderWithProviders(
      <GoalProposalMessage
        actor={{ kind: "claude", initial: "CC", displayName: "claude" }}
        message={sample}
      />,
    );
    expect(screen.getByText(/30 分钟 talk/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Set as goal/i })).toBeInTheDocument();
  });

  it("adopts the goal on click", async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <GoalProposalMessage
        actor={{ kind: "claude", initial: "CC", displayName: "claude" }}
        message={sample}
      />,
    );
    await user.click(screen.getByRole("button", { name: /Set as goal/i }));
    await waitFor(() => {
      expect(screen.getByText(/Adopted/i)).toBeInTheDocument();
    });
  });
});
