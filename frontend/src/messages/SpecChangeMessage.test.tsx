import { describe, it, expect } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../test/render";
import { SpecChangeMessage } from "./SpecChangeMessage";

describe("<SpecChangeMessage />", () => {
  it("renders file + before/after + approvers", () => {
    renderWithProviders(
      <SpecChangeMessage
        actor={{ kind: "codex", initial: "CX", displayName: "codex" }}
        message={{
          id: 8, topic_id: 1, type: "spec_change", actor_type: "agent", actor_id: 13,
          body: "字号 10 → 14",
          metadata: { file: ".claude/skills/x", before: 10, after: 14, approvers: ["Trinity"] },
          ref_event_id: null, created_at: "2026-05-19T10:28:00Z",
        }}
      />,
    );
    expect(screen.getByText("Trinity")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Approve/ })).toBeInTheDocument();
  });

  it("posts a decision message when Approve is clicked", async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <SpecChangeMessage
        actor={{ kind: "codex", initial: "CX", displayName: "codex" }}
        message={{
          id: 8, topic_id: 1, type: "spec_change", actor_type: "agent", actor_id: 13,
          body: "字号 10 → 14",
          metadata: { file: ".claude/skills/x", before: 10, after: 14, approvers: ["Trinity"] },
          ref_event_id: null, created_at: "2026-05-19T10:28:00Z",
        }}
      />,
    );
    await user.click(screen.getByRole("button", { name: /Approve/ }));
    await waitFor(() => {
      expect(screen.getByText(/Approved/)).toBeInTheDocument();
    });
  });
});
