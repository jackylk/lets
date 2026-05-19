import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { ReviewMessage } from "./ReviewMessage";

describe("<ReviewMessage />", () => {
  it("renders review tag and ref note", () => {
    renderWithProviders(
      <ReviewMessage
        actor={{ kind: "codex", initial: "CX", displayName: "codex" }}
        message={{
          id: 13, topic_id: 1, type: "review", actor_type: "agent", actor_id: 13,
          body: "建议把事件性放最前", metadata: { ref_message_id: 11 },
          ref_event_id: null, created_at: "2026-05-19T11:05:00Z",
        }}
      />,
    );
    expect(screen.getByText(/review/)).toBeInTheDocument();
    expect(screen.getByText(/↳ #11/)).toBeInTheDocument();
  });
});
