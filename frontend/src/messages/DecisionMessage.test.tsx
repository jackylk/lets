import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { DecisionMessage } from "./DecisionMessage";

describe("<DecisionMessage />", () => {
  it("shows decision type and ref id", () => {
    renderWithProviders(
      <DecisionMessage
        actor={{ kind: "human", initial: "N", displayName: "Neo" }}
        message={{
          id: 10, topic_id: 1, type: "decision", actor_type: "human", actor_id: 1,
          body: "approve spec change v2 → v3",
          metadata: { decision_type: "adopt", ref_message_id: 8 },
          ref_event_id: null, created_at: "2026-05-19T10:35:00Z",
        }}
      />,
    );
    expect(screen.getByText("decision · adopt")).toBeInTheDocument();
    expect(screen.getByText(/approve spec change/)).toBeInTheDocument();
  });
});
