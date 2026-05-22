import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../test/render";
import { BottomTabs } from "./BottomTabs";

describe("<BottomTabs />", () => {
  it("renders mobile tabs and fires onSelect", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    renderWithProviders(<BottomTabs active="topic" onSelect={onSelect} />);
    expect(screen.getByRole("button", { name: /工作区/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /话题/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /注意/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /上下文/ })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /注意/ }));
    expect(onSelect).toHaveBeenCalledWith("attention");
  });
});
