import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { ProactiveFindingMessage } from "./ProactiveFindingMessage";

describe("<ProactiveFindingMessage />", () => {
  it("renders proactive tag", () => {
    renderWithProviders(
      <ProactiveFindingMessage
        actor={{ kind: "claude", initial: "CC", displayName: "claude" }}
        message={{
          id: 7, topic_id: 1, type: "proactive_finding", actor_type: "agent", actor_id: 12,
          body: "v3 slide 5 建议加文字", metadata: {},
          ref_event_id: null, created_at: "2026-05-19T10:20:00Z",
        }}
      />,
    );
    expect(screen.getByText("proactive")).toBeInTheDocument();
  });
});
