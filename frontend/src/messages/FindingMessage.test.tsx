import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { FindingMessage } from "./FindingMessage";

describe("<FindingMessage />", () => {
  it("renders finding tag + body", () => {
    renderWithProviders(
      <FindingMessage
        actor={{ kind: "claude", initial: "CC", displayName: "claude" }}
        message={{
          id: 4, topic_id: 1, type: "finding", actor_type: "agent", actor_id: 12,
          body: "图太多文字太少", metadata: {}, ref_event_id: null,
          created_at: "2026-05-19T09:46:00Z",
        }}
      />,
    );
    expect(screen.getByText("finding")).toBeInTheDocument();
  });
});
