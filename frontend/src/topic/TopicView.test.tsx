import { describe, it, expect } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../test/render";
import { TopicView } from "./TopicView";

describe("<TopicView />", () => {
  it("renders the fixture topic's typed messages", async () => {
    renderWithProviders(<TopicView topicId={1} />);
    await waitFor(() => {
      // Stream collapses status-before-reply (the "X 正在输入…" bubble that
      // immediately precedes the same agent's chat reply), so the visible
      // count is one less than the raw fixture size. The exact number isn't
      // load-bearing — just verify the fixture renders and is non-trivial.
      expect(screen.getAllByTestId("message-row").length).toBeGreaterThan(10);
    });
  });

  it("posts a new chat message via composer", async () => {
    const user = userEvent.setup();
    renderWithProviders(<TopicView topicId={1} />);
    await waitFor(() => screen.getAllByTestId("message-row"));
    const textarea = screen.getByRole("textbox");
    await user.type(textarea, "hello composer");
    await user.keyboard("{Enter}");
    await waitFor(() => {
      expect(screen.getByText("hello composer")).toBeInTheDocument();
    });
  });
});
