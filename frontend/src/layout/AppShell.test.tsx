import { beforeEach, describe, it, expect } from "vitest";
import { fireEvent, screen } from "@testing-library/react";
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
    // Context is in the DOM even when the drawer is closed (so it can animate).
    expect(screen.getByText("CTX")).toBeInTheDocument();
  });

  it("annotates the grid container for breakpoint switching", () => {
    renderWithProviders(<AppShell sidebar={<i />} main={<i />} context={<i />} />);
    const grid = screen.getByTestId("app-shell");
    expect(grid.className).toContain("grid");
  });

  it("starts with the context drawer collapsed (aria-hidden + toggle visible)", () => {
    renderWithProviders(
      <AppShell sidebar={<i />} main={<i />} context={<div>CTX</div>} />,
    );
    expect(screen.getByTestId("app-context").getAttribute("aria-hidden")).toBe("true");
    expect(screen.getByTestId("app-context-toggle")).toBeInTheDocument();
  });

  it("opens the drawer when the toggle is clicked", () => {
    renderWithProviders(
      <AppShell sidebar={<i />} main={<i />} context={<div>CTX</div>} />,
    );
    fireEvent.click(screen.getByTestId("app-context-toggle"));
    expect(screen.getByTestId("app-context").getAttribute("aria-hidden")).toBe("false");
    expect(screen.queryByTestId("app-context-toggle")).toBeNull();
  });
});
