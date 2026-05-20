import { describe, it, expect } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { GoalDetailPanel } from "./GoalDetailPanel";

describe("<GoalDetailPanel />", () => {
  it("renders the seeded goal spec for topic 1", async () => {
    renderWithProviders(<GoalDetailPanel topicId={1} />);
    await waitFor(() => {
      expect(screen.getByText(/30 分钟 talk/)).toBeInTheDocument();
    });
  });

  it("renders empty state when no tree exists (topic 9999)", async () => {
    renderWithProviders(<GoalDetailPanel topicId={9999} />);
    await waitFor(() => {
      expect(screen.getByText(/尚未设定目标/)).toBeInTheDocument();
    });
  });
});
