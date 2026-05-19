import { describe, it, expect } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../test/render";
import { SettingsTokensPage } from "./SettingsTokensPage";

describe("<SettingsTokensPage />", () => {
  it("starts empty, creates a token, reveals the raw value once", async () => {
    const user = userEvent.setup();
    renderWithProviders(<SettingsTokensPage />);
    await waitFor(() => expect(screen.getByText(/No agent tokens yet/i)).toBeInTheDocument());

    await user.click(screen.getByRole("button", { name: /\+ New token/i }));
    await user.type(screen.getByLabelText(/Label/i), "claude on neo-mbp");
    await user.selectOptions(screen.getByLabelText(/Role/i), "claude");
    await user.type(screen.getByLabelText(/Device/i), "neo-mbp");
    await user.click(screen.getByRole("button", { name: /^Create$/ }));

    // Token reveal modal
    await waitFor(() => {
      expect(screen.getByText(/copy now — it won't show again/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/^lets_/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Done/i }));
    await waitFor(() => expect(screen.getByText(/claude on neo-mbp/)).toBeInTheDocument());
  });

  it("revokes a token", async () => {
    const user = userEvent.setup();
    renderWithProviders(<SettingsTokensPage />);
    await user.click(screen.getByRole("button", { name: /\+ New token/i }));
    await user.type(screen.getByLabelText(/Label/i), "to-revoke");
    await user.selectOptions(screen.getByLabelText(/Role/i), "codex");
    await user.type(screen.getByLabelText(/Device/i), "neo-mbp");
    await user.click(screen.getByRole("button", { name: /^Create$/ }));
    await user.click(screen.getByRole("button", { name: /Done/i }));

    await user.click(screen.getByRole("button", { name: /Revoke/i }));
    await waitFor(() => {
      expect(screen.getByText(/revoked/i)).toBeInTheDocument();
    });
  });
});
