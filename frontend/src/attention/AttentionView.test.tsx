import { describe, it, expect } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { AttentionView } from "./AttentionView";

describe("<AttentionView />", () => {
  it("renders greeting + 3 groups", async () => {
    renderWithProviders(<AttentionView userName="Neo" />);
    await waitFor(() => {
      expect(screen.getByText(/早上好，Neo/)).toBeInTheDocument();
    });
    expect(screen.getByRole("heading", { name: /需要决定/ })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /主动发现/ })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /同事消息/ })).toBeInTheDocument();
  });
});
