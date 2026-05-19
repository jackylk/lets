import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../test/render";
import { GoalDetailPanel } from "./GoalDetailPanel";

describe("<GoalDetailPanel />", () => {
  it("renders artifact name, spec, approvers, and final button", async () => {
    const onMarkFinal = vi.fn();
    const user = userEvent.setup();
    renderWithProviders(
      <GoalDetailPanel
        artifactName="ai-memory-talk.pptx"
        artifactVersion="v3"
        spec="30 分钟 talk · 技术受众 · 突出「事件性记忆 vs 语义记忆」"
        approvers={["Trinity", "Morpheus", "Neo"]}
        onMarkFinal={onMarkFinal}
        onProposeChange={() => {}}
      />,
    );
    expect(screen.getByText("ai-memory-talk.pptx")).toBeInTheDocument();
    expect(screen.getByText(/30 分钟/)).toBeInTheDocument();
    expect(screen.getByText("Trinity")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Mark as Final/ }));
    expect(onMarkFinal).toHaveBeenCalledTimes(1);
  });
});
