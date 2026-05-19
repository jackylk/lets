import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { HandoffMessage } from "./HandoffMessage";

describe("<HandoffMessage />", () => {
  it("renders handoff tag with from→to", () => {
    renderWithProviders(
      <HandoffMessage
        actor={{ kind: "claude", initial: "CC", displayName: "claude" }}
        message={{
          id: 11, topic_id: 1, type: "handoff", actor_type: "agent", actor_id: 11,
          body: "P5 文字解释 @codex 接一下",
          metadata: { from_actor_id: 11, to_actor_id: 13 },
          ref_event_id: null, created_at: "2026-05-19T10:40:00Z",
        }}
      />,
    );
    expect(screen.getByText(/handoff/)).toBeInTheDocument();
    expect(screen.getByText(/#11.*#13/)).toBeInTheDocument();
  });
});
