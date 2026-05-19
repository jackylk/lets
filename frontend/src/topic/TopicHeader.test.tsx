import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { TopicHeader } from "./TopicHeader";

describe("<TopicHeader />", () => {
  it("renders topic title", () => {
    renderWithProviders(<TopicHeader title="为 Agent 记忆写一个研讨 PPT" />);
    expect(screen.getByRole("heading", { name: /PPT/ })).toBeInTheDocument();
  });

  it("renders progress percent + count when goal info present", () => {
    renderWithProviders(
      <TopicHeader
        title="t"
        goal={{ doneCount: 5, totalCount: 7, currentTaskTitle: "P5 加文字解释" }}
      />,
    );
    expect(screen.getByText(/71%/)).toBeInTheDocument();
    expect(screen.getByText(/5\s*\/\s*7/)).toBeInTheDocument();
    expect(screen.getByText(/P5/)).toBeInTheDocument();
  });

  it("omits goal chip when no goal info", () => {
    renderWithProviders(<TopicHeader title="t" />);
    expect(screen.queryByText(/%/)).not.toBeInTheDocument();
  });
});
