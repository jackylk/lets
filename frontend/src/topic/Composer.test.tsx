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
    expect(onSend).toHaveBeenCalledWith({ body: "hello", addressedTo: null });
    expect((textarea as HTMLTextAreaElement).value).toBe("");
  });

  it("extracts @mentions and feeds resolved human_ids into addressedTo", async () => {
    const onSend = vi.fn();
    const resolver = {
      resolveHumanIds: vi.fn((mentions: string[]) => {
        const map: Record<string, number> = { cc: 1, codex: 1, jacky: 1, trinity: 2 };
        return mentions.map((m) => map[m]).filter((n): n is number => typeof n === "number");
      }),
    };
    const user = userEvent.setup();
    renderWithProviders(<Composer onSend={onSend} resolver={resolver} />);

    const textarea = screen.getByRole("textbox");
    await user.type(textarea, "@cc 你能帮我看看吗？ @trinity");
    await user.keyboard("{Enter}");

    expect(resolver.resolveHumanIds).toHaveBeenCalledWith(["cc", "trinity"]);
    expect(onSend).toHaveBeenCalledWith({
      body: "@cc 你能帮我看看吗？ @trinity",
      addressedTo: "1,2",
    });
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
