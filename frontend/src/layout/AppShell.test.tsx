import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { AppShell } from "./AppShell";

describe("<AppShell />", () => {
  it("renders the 3 named slots", () => {
    renderWithProviders(
      <AppShell
        sidebar={<div>SIDE</div>}
        main={<div>MAIN</div>}
        context={<div>CTX</div>}
      />,
    );
    expect(screen.getByText("SIDE")).toBeInTheDocument();
    expect(screen.getByText("MAIN")).toBeInTheDocument();
    expect(screen.getByText("CTX")).toBeInTheDocument();
  });

  it("annotates the grid container for breakpoint switching", () => {
    renderWithProviders(<AppShell sidebar={<i />} main={<i />} context={<i />} />);
    const grid = screen.getByTestId("app-shell");
    expect(grid.className).toContain("grid");
  });
});
