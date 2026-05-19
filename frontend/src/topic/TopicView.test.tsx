import { describe, it, expect } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { TopicView } from "./TopicView";

describe("<TopicView />", () => {
  it("renders topic header + 14 message rows for topic 1", async () => {
    renderWithProviders(<TopicView topicId={1} />);
    await waitFor(() => {
      expect(screen.getAllByTestId("message-row").length).toBe(14);
    });
  });
});
