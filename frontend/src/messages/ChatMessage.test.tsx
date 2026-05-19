import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { ChatMessage } from "./ChatMessage";

describe("<ChatMessage />", () => {
  it("renders body with mentions parsed", () => {
    renderWithProviders(
      <ChatMessage
        actor={{ kind: "human", initial: "N", displayName: "Neo" }}
        message={{
          id: 1, topic_id: 1, type: "chat", actor_type: "human", actor_id: 1,
          body: "ping @Trinity", metadata: {}, ref_event_id: null, created_at: "2026-05-19T09:14:00Z",
        }}
      />,
    );
    expect(screen.getByText("@Trinity")).toHaveClass("mention");
  });
});
