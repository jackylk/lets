import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { Sidebar } from "./Sidebar";

describe("<Sidebar />", () => {
  it("renders the Let's masthead + tagline", () => {
    renderWithProviders(<Sidebar topics={[]} activeTopicId={null} />);
    expect(screen.getByText("Let's")).toBeInTheDocument();
    expect(screen.getByText(/humans \+ agents/i)).toBeInTheDocument();
  });

  it("shows section labels for topics and agents", () => {
    renderWithProviders(<Sidebar topics={[]} activeTopicId={null} />);
    // The 话题 section header toggle + "+" new-topic button both match /话题/;
    // use getAllByRole + at least 1 assertion.
    expect(screen.getAllByRole("button", { name: /话题/ }).length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: /Agent/ })).toBeInTheDocument();
  });

  it("no longer renders the 待处理 entry (removed from sidebar)", () => {
    renderWithProviders(<Sidebar topics={[]} activeTopicId={null} />);
    expect(screen.queryByRole("button", { name: /待处理/ })).toBeNull();
  });
});
