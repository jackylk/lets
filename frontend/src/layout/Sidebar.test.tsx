import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { Sidebar } from "./Sidebar";

describe("<Sidebar />", () => {
  it("renders project name + repo line", () => {
    renderWithProviders(<Sidebar projectName="Lets" projectRepo="github.com/echomem/lets" />);
    expect(screen.getByText("Lets")).toBeInTheDocument();
    expect(screen.getByText(/echomem\/lets/)).toBeInTheDocument();
  });

  it("shows section labels for channels, online, direct", () => {
    renderWithProviders(<Sidebar projectName="Lets" projectRepo="x/y" />);
    expect(screen.getByText(/channels/i)).toBeInTheDocument();
    expect(screen.getByText(/online/i)).toBeInTheDocument();
    expect(screen.getByText(/direct/i)).toBeInTheDocument();
  });

  it("renders the attention entry button", () => {
    renderWithProviders(<Sidebar projectName="Lets" projectRepo="x/y" />);
    expect(screen.getByRole("button", { name: /待处理|attention/i })).toBeInTheDocument();
  });
});
