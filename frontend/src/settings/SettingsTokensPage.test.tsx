import { describe, it, expect } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../test/render";
import { SettingsTokensPage } from "./SettingsTokensPage";

describe("<SettingsTokensPage />", () => {
  it("shows the install + lets-add commands instead of minting a token via the UI", async () => {
    const user = userEvent.setup();
    renderWithProviders(<SettingsTokensPage />);
    await waitFor(() => expect(screen.getByText(/还没有接入任何电脑/i)).toBeInTheDocument());

    await user.click(screen.getByRole("button", { name: /\+ 添加/i }));

    // Default Claude: shows the full curl one-liner for first-time install
    // and the shorter `lets add claude` form for already-installed users.
    expect(
      screen.getByText((text) => text.includes("curl -fsSL") && text.includes("/install | bash")),
    ).toBeInTheDocument();
    expect(screen.getByText("lets add claude")).toBeInTheDocument();

    // Switch to Codex and confirm both commands update.
    await user.selectOptions(screen.getByRole("combobox"), "codex");
    expect(
      screen.getByText((text) => text.includes("LETS_AGENT_ROLE=codex")),
    ).toBeInTheDocument();
    expect(screen.getByText("lets add codex")).toBeInTheDocument();
  });

  it("revokes a token that already exists", async () => {
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
      expect(screen.getByText(/已移除/i)).toBeInTheDocument();
    });
  });
});
