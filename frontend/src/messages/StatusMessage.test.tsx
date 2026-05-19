import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { StatusMessage } from "./StatusMessage";

describe("<StatusMessage />", () => {
  it("shows status tag and body", () => {
    renderWithProviders(
      <StatusMessage
        actor={{ kind: "claude", initial: "CC", displayName: "claude · neo-mbp" }}
        message={{
          id: 2, topic_id: 1, type: "status", actor_type: "agent", actor_id: 11,
          body: "active · 读 docs", metadata: { agent_status: "active" },
          ref_event_id: null, created_at: "2026-05-19T09:18:00Z",
        }}
      />,
    );
    expect(screen.getByText("status")).toBeInTheDocument();
    expect(screen.getByText(/active · 读 docs/)).toBeInTheDocument();
  });
});
