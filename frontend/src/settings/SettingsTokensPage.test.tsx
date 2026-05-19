import { describe, it, expect } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../test/render";
import { SettingsTokensPage } from "./SettingsTokensPage";

describe("<SettingsTokensPage />", () => {
  it("starts empty, creates a token, reveals the raw value once", async () => {
    const user = userEvent.setup();
    renderWithProviders(<SettingsTokensPage />);
    await waitFor(() => expect(screen.getByText(/还没有连接任何电脑/i)).toBeInTheDocument());

    await user.click(screen.getByRole("button", { name: /\+ 添加/i }));
    await user.selectOptions(screen.getByLabelText(/Agent/i), "claude");
    await user.type(screen.getByLabelText(/电脑名称/i), "neo-mbp");
    await user.click(screen.getByRole("button", { name: /^添加$/ }));

    await waitFor(() => {
      expect(screen.getByText(/复制连接密钥/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/^lets_/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /完成/i }));
    await waitFor(() => expect(screen.getAllByText("Claude Code").length).toBeGreaterThan(0));
    expect(screen.getByText(/neo-mbp/)).toBeInTheDocument();
  });

  it("revokes a token", async () => {
    const user = userEvent.setup();
    renderWithProviders(<SettingsTokensPage />);
    await user.click(screen.getByRole("button", { name: /\+ 添加/i }));
    await user.selectOptions(screen.getByLabelText(/Agent/i), "codex");
    await user.type(screen.getByLabelText(/电脑名称/i), "neo-mbp");
    await user.click(screen.getByRole("button", { name: /^添加$/ }));
    await user.click(screen.getByRole("button", { name: /完成/i }));

    await user.click(screen.getByRole("button", { name: /移除/i }));
    await waitFor(() => {
      expect(screen.getByText(/已移除/i)).toBeInTheDocument();
    });
  });
});
