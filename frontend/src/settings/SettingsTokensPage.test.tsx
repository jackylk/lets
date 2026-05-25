import { describe, it, expect } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../test/render";
import { SettingsTokensPage } from "./SettingsTokensPage";

describe("<SettingsTokensPage />", () => {
  it("lets the current member update their account name", async () => {
    const user = userEvent.setup();
    renderWithProviders(<SettingsTokensPage />);
    const input = await screen.findByRole("textbox", { name: /名字/i });
    expect(input).toHaveValue("Neo");

    await user.clear(input);
    await user.type(input, "Jacky Li");
    await user.click(screen.getByRole("button", { name: /^保存$/ }));

    await waitFor(() => expect(input).toHaveValue("Jacky Li"));
    expect(screen.getByText("已保存为 Jacky Li")).toBeInTheDocument();
  });

  it("shows the install + lets-add commands instead of minting a token via the UI", async () => {
    const user = userEvent.setup();
    renderWithProviders(<SettingsTokensPage />);
    await waitFor(() => expect(screen.getByText(/还没有接入任何电脑/i)).toBeInTheDocument());

    await user.click(screen.getByRole("button", { name: /\+ 添加/i }));

    // Installing lets is separate from adding a local agent.
    expect(
      screen.getByText((text) =>
        text.includes("curl -fsSL") &&
        text.includes("/install | bash"),
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("lets add claude")).toBeInTheDocument();

    await user.selectOptions(screen.getByRole("combobox", { name: /Claude 模型/i }), "sonnet-4.6");
    expect(
      screen.getByText((text) =>
        text.includes("curl -fsSL") &&
        text.includes("/install | bash"),
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("lets add claude --model sonnet-4.6")).toBeInTheDocument();

    // Switch to Codex and confirm only the add command depends on role/model.
    await user.selectOptions(screen.getByRole("combobox", { name: /Agent 类型/i }), "codex");
    expect(
      screen.getByText((text) =>
        text.includes("curl -fsSL") &&
        text.includes("/install | bash"),
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("lets add codex")).toBeInTheDocument();

    await user.clear(screen.getByRole("textbox", { name: /Codex 模型/i }));
    await user.type(screen.getByRole("textbox", { name: /Codex 模型/i }), "o3");
    expect(screen.getByText("lets add codex --model o3")).toBeInTheDocument();
  });

  it("lets the user update an existing Claude agent model", async () => {
    await fetch("/api/tokens", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        label: "claude on mac16",
        role: "claude",
        device_label: "mac16",
        model: "haiku",
      }),
    });

    const user = userEvent.setup();
    renderWithProviders(<SettingsTokensPage />);
    const select = await screen.findByRole("combobox", { name: /mac16 模型/i });
    expect(await screen.findByText("Neo")).toBeInTheDocument();
    expect(screen.getByText("Claude Code")).toBeInTheDocument();
    expect(select).toHaveValue("haiku");

    await user.selectOptions(select, "sonnet-4.6");
    await waitFor(() => expect(select).toHaveValue("sonnet-4.6"));
  });

  it("removes an existing agent from the settings list", async () => {
    // The agent list reflects whatever the backend already knows about, so
    // we pre-seed via the MSW handler by POSTing a token before rendering.
    await fetch("/api/tokens", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        label: "codex on neo-mbp",
        role: "codex",
        device_label: "neo-mbp",
      }),
    });

    const user = userEvent.setup();
    renderWithProviders(<SettingsTokensPage />);
    await waitFor(() => expect(screen.getByText(/neo-mbp/)).toBeInTheDocument());

    await user.click(screen.getByRole("button", { name: /移除/i }));
    await waitFor(() => {
      expect(screen.queryByText(/neo-mbp/)).not.toBeInTheDocument();
    });
    expect(screen.queryByText(/已移除/i)).not.toBeInTheDocument();
  });
});
