import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { Sidebar } from "./Sidebar";

describe("<Sidebar />", () => {
  it("renders project name + repo line", () => {
    renderWithProviders(
      <Sidebar
        projectName="Lets"
        projectRepo="github.com/echomem/lets"
        topics={[]}
        activeTopicId={null}
      />,
    );
    expect(screen.getByText("Lets")).toBeInTheDocument();
    expect(screen.getByText(/echomem\/lets/)).toBeInTheDocument();
  });

  it("shows section labels for topics and agents", () => {
    renderWithProviders(
      <Sidebar projectName="Lets" projectRepo="x/y" topics={[]} activeTopicId={null} />,
    );
    // The 话题 section header toggle + "+" new-topic button both match /话题/;
    // use getAllByRole + at least 1 assertion.
    expect(screen.getAllByRole("button", { name: /话题/ }).length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: /Agent/ })).toBeInTheDocument();
  });

  it("renders the attention entry button", () => {
    renderWithProviders(
      <Sidebar projectName="Lets" projectRepo="x/y" topics={[]} activeTopicId={null} />,
    );
    expect(screen.getByRole("button", { name: /待处理|attention/i })).toBeInTheDocument();
  });
});
