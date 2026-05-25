import { beforeEach, describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { AppShell } from "./AppShell";

describe("<AppShell />", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

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

  it("locks the app shell to the viewport instead of the document scroll", () => {
    renderWithProviders(<AppShell sidebar={<i />} main={<i />} context={<i />} />);
    const grid = screen.getByTestId("app-shell");
    expect(grid.className).toContain("fixed");
    expect(grid.className).toContain("inset-0");
    expect(grid.className).toContain("overflow-hidden");
  });

  it("keeps the context panel in the desktop grid", () => {
    renderWithProviders(
      <AppShell sidebar={<i />} main={<i />} context={<div>CTX</div>} />,
    );
    expect(screen.getByTestId("app-context").getAttribute("aria-hidden")).toBe("false");
    expect(screen.getByTestId("app-shell").getAttribute("style")).toContain("minmax(0, 1fr)");
    expect(screen.queryByTestId("app-context-toggle")).toBeNull();
  });
});
