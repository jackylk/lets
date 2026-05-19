import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../test/render";
import { BottomTabs } from "./BottomTabs";

describe("<BottomTabs />", () => {
  it("renders 3 tabs and fires onSelect", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    renderWithProviders(<BottomTabs active="topic" onSelect={onSelect} />);
    expect(screen.getByRole("button", { name: /Topic/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Attention/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Context/ })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Attention/ }));
    expect(onSelect).toHaveBeenCalledWith("attention");
  });
});
