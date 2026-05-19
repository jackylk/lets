import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { TaskTreePanel } from "./TaskTreePanel";

describe("<TaskTreePanel />", () => {
  it("renders title + progress + rows", () => {
    renderWithProviders(
      <TaskTreePanel
        title="研讨 PPT 终版"
        items={[
          { title: "Framing", status: "done" },
          { title: "矩阵", status: "active", owner_name: "claude" },
          { title: "排练", status: "pending" },
        ]}
      />,
    );
    expect(screen.getByText("研讨 PPT 终版")).toBeInTheDocument();
    expect(screen.getByText(/1 \/ 3/)).toBeInTheDocument();
    expect(screen.getByText("claude")).toBeInTheDocument();
  });
});
