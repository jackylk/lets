import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { NudgeMessage } from "./NudgeMessage";

describe("<NudgeMessage />", () => {
  it("renders nudge tag and reason", () => {
    renderWithProviders(
      <NudgeMessage
        actor={{ kind: "system", initial: "S", displayName: "system" }}
        message={{
          id: 12, topic_id: 1, type: "nudge", actor_type: "system", actor_id: null,
          body: "讨论 framing 25 分钟", metadata: { reason: "framing-loop" },
          ref_event_id: null, created_at: "2026-05-19T10:50:00Z",
        }}
      />,
    );
    expect(screen.getByText(/nudge/)).toBeInTheDocument();
    expect(screen.getByText(/framing-loop/)).toBeInTheDocument();
  });
});
