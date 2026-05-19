import { describe, it, expect } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../test/render";
import { TopicView } from "./TopicView";

describe("<TopicView />", () => {
  it("renders 14 typed messages for topic 1", async () => {
    renderWithProviders(<TopicView topicId={1} topicTitle="t" />);
    await waitFor(() => {
      expect(screen.getAllByTestId("message-row").length).toBe(14);
    });
  });

  it("posts a new chat message via composer", async () => {
    const user = userEvent.setup();
    renderWithProviders(<TopicView topicId={1} topicTitle="t" />);
    await waitFor(() => screen.getAllByTestId("message-row"));
    const textarea = screen.getByRole("textbox");
    await user.type(textarea, "hello composer");
    await user.keyboard("{Enter}");
    await waitFor(() => {
      expect(screen.getByText("hello composer")).toBeInTheDocument();
    });
  });
});
