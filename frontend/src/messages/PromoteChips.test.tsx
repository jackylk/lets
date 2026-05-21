import { describe, it, expect } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../test/render";
import { PromoteChips } from "./PromoteChips";

describe("<PromoteChips />", () => {
  it("renders the four promote buttons", () => {
    renderWithProviders(
      <PromoteChips topicId={1} sourceMessageId={42} sourceBody="agent reply text" />,
    );
    expect(screen.getByRole("button", { name: "+ 共识" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "+ 候选" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "+ 待问" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "+ 约束" })).toBeInTheDocument();
  });

  it("opens an editor pre-filled with the agent's first line on click", async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <PromoteChips
        topicId={1}
        sourceMessageId={42}
        sourceBody="第一行：建议走 SAML 方案\n第二行其它说明"
      />,
    );
    await user.click(screen.getByRole("button", { name: "+ 共识" }));
    const textarea = screen.getByTestId("promote-input") as HTMLTextAreaElement;
    expect(textarea.value).toMatch(/SAML/);
    // Submit button visible
    expect(screen.getByRole("button", { name: "确认" })).toBeInTheDocument();
  });

  it("cancel closes the editor", async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <PromoteChips topicId={1} sourceMessageId={42} sourceBody="hi" />,
    );
    await user.click(screen.getByRole("button", { name: "+ 候选" }));
    await user.click(screen.getByRole("button", { name: "取消" }));
    await waitFor(() => {
      expect(screen.queryByTestId("promote-input")).toBeNull();
    });
  });
});
