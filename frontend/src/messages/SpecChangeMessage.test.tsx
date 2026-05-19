import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
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
          metadata: {
            file: ".claude/skills/research-talk-style/SKILL.md",
            before: 10, after: 14, approvers: ["Trinity"],
          },
          ref_event_id: null, created_at: "2026-05-19T10:28:00Z",
        }}
      />,
    );
    expect(screen.getByText(/research-talk-style/)).toBeInTheDocument();
    expect(screen.getAllByText("10").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("14").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/Trinity/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /approve/i })).toBeInTheDocument();
  });
});
