import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { SystemMessage } from "./SystemMessage";

describe("<SystemMessage />", () => {
  it("renders body in muted style with no avatar block", () => {
    renderWithProviders(
      <SystemMessage
        actor={{ kind: "system", initial: "S", displayName: "system" }}
        message={{
          id: 14, topic_id: 1, type: "system", actor_type: "system", actor_id: null,
          body: "Trinity 加入了 topic", metadata: {}, ref_event_id: null, created_at: "2026-05-19T11:10:00Z",
        }}
      />,
    );
    expect(screen.getByText(/Trinity 加入了 topic/)).toBeInTheDocument();
  });
});
