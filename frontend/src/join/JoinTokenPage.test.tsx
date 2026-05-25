import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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
    const mockFetch = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ "content-type": "application/json" }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ workspace_id: 42, topic_id: 99 }),
      });
    vi.stubGlobal("fetch", mockFetch);

    render(<JoinTokenPage token="abc123" />);
    expect(screen.getByText(/加入工作区中/)).toBeInTheDocument();
    await waitFor(() => {
      expect(window.location.href).toContain("workspace=42");
      expect(window.location.href).toContain("topic=99");
    });

    vi.unstubAllGlobals();
  });

  it("lets a signed-out participant join as guest", async () => {
    const mockFetch = vi
      .fn()
      .mockResolvedValueOnce({ ok: false })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ workspace_id: 42 }),
      });
    vi.stubGlobal("fetch", mockFetch);

    render(<JoinTokenPage token="abc123" />);
    await screen.findByText("作为访客加入");
    fireEvent.change(screen.getByLabelText("你的名字"), { target: { value: "Sam" } });
    fireEvent.click(screen.getByText("作为访客加入"));

    await waitFor(() => {
      expect(window.location.href).toContain("workspace=42");
    });
    expect(mockFetch).toHaveBeenLastCalledWith(
      "/api/invites/abc123/accept-guest",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ name: "Sam" }),
      }),
    );

    vi.unstubAllGlobals();
  });
});
