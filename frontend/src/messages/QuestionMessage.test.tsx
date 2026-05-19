import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { QuestionMessage } from "./QuestionMessage";

describe("<QuestionMessage />", () => {
  it("renders question tag", () => {
    renderWithProviders(
      <QuestionMessage
        actor={{ kind: "human", initial: "M", displayName: "Morpheus" }}
        message={{
          id: 5, topic_id: 1, type: "question", actor_type: "human", actor_id: 3,
          body: "?", metadata: {}, ref_event_id: null,
          created_at: "2026-05-19T09:55:00Z",
        }}
      />,
    );
    expect(screen.getByText("question")).toBeInTheDocument();
  });
});
