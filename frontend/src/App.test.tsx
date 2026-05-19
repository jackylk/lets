import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../test/render";
import App from "./App";

describe("<App />", () => {
  it("renders the Lets heading", () => {
    renderWithProviders(<App />);
    expect(screen.getByRole("heading", { name: /lets/i })).toBeInTheDocument();
  });
});
