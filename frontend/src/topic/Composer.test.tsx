import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../test/render";
import { Composer } from "./Composer";

describe("<Composer />", () => {
  it("calls onSend with text on Enter; submit button enables when text present", async () => {
    const onSend = vi.fn();
    const user = userEvent.setup();
    renderWithProviders(<Composer onSend={onSend} />);

    const textarea = screen.getByRole("textbox");
    const button = screen.getByRole("button", { name: /发送/ });

    expect(button).toBeDisabled();
    await user.type(textarea, "hello");
    expect(button).toBeEnabled();

    await user.keyboard("{Enter}");
    expect(onSend).toHaveBeenCalledWith("hello");
    expect((textarea as HTMLTextAreaElement).value).toBe("");
  });

  it("Shift+Enter inserts newline without sending", async () => {
    const onSend = vi.fn();
    const user = userEvent.setup();
    renderWithProviders(<Composer onSend={onSend} />);
    const textarea = screen.getByRole("textbox");
    await user.type(textarea, "line1");
    await user.keyboard("{Shift>}{Enter}{/Shift}line2");
    expect(onSend).not.toHaveBeenCalled();
    expect((textarea as HTMLTextAreaElement).value).toBe("line1\nline2");
  });
});
