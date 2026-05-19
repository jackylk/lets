import { describe, it, expect } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { TopicView } from "./TopicView";

describe("<TopicView />", () => {
  it("renders 14 typed messages for topic 1", async () => {
    renderWithProviders(<TopicView topicId={1} topicTitle="t" />);
    await waitFor(() => {
      expect(screen.getAllByTestId("message-row").length).toBe(14);
    });
  });

  it("renders artifact_revision message inline with slide thumbnails", async () => {
    renderWithProviders(<TopicView topicId={1} topicTitle="t" />);
    await waitFor(() => {
      expect(screen.getByText("ai-memory-talk.pptx")).toBeInTheDocument();
    });
  });
});
