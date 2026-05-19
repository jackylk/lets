import { describe, it, expect } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { renderWithProviders } from "../test/render";
import App from "./App";

describe("<App />", () => {
  it("renders the topic title in the header", async () => {
    renderWithProviders(<App />);
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /PPT/ })).toBeInTheDocument();
    });
  });
});
