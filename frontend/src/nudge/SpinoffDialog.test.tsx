import { describe, it, expect, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../test/render";
import { SpinoffDialog } from "./SpinoffDialog";

describe("<SpinoffDialog />", () => {
  it("submits title and fires onSubmit", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    const onCancel = vi.fn();
    renderWithProviders(
      <SpinoffDialog
        suggestedTitle="周五团建"
        onSubmit={onSubmit}
        onCancel={onCancel}
      />,
    );
    const input = screen.getByLabelText(/新 topic 标题/);
    expect((input as HTMLInputElement).value).toBe("周五团建");
    await user.click(screen.getByRole("button", { name: /创建/ }));
    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith("周五团建");
    });
  });

  it("calls onCancel from cancel button", async () => {
    const user = userEvent.setup();
    const onCancel = vi.fn();
    renderWithProviders(
      <SpinoffDialog
        suggestedTitle="t"
        onSubmit={vi.fn()}
        onCancel={onCancel}
      />,
    );
    await user.click(screen.getByRole("button", { name: /取消/ }));
    expect(onCancel).toHaveBeenCalled();
  });
});
