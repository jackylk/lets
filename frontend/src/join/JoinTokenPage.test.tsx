import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { JoinTokenPage } from "./JoinTokenPage";

describe("JoinTokenPage", () => {
  let originalLocation: Location;

  beforeEach(() => {
    originalLocation = window.location;
    Object.defineProperty(window, "location", {
      value: { href: "/join/abc123", pathname: "/join/abc123" },
      writable: true,
      configurable: true,
    });
  });

  afterEach(() => {
    Object.defineProperty(window, "location", {
      value: originalLocation,
      writable: true,
      configurable: true,
    });
  });

  it("shows loading then redirects after accept", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ workspace_id: 42 }),
    });
    vi.stubGlobal("fetch", mockFetch);

    render(<JoinTokenPage token="abc123" />);
    expect(screen.getByText(/加入工作区中/)).toBeInTheDocument();
    await waitFor(() => {
      expect(window.location.href).toContain("workspace=42");
    });

    vi.unstubAllGlobals();
  });
});
