import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { LoginPage } from "./LoginPage";

describe("<LoginPage />", () => {
  it("renders Login with GitHub button pointing to /auth/github/start", async () => {
    renderWithProviders(<LoginPage />);
    const link = await screen.findByRole("link", { name: /Sign in with GitHub/i });
    expect(link).toHaveAttribute("href", "/auth/github/start");
  });

  it("uses dev login when local dev sessions are enabled", async () => {
    renderWithProviders(
      <LoginPage initialContext={{ auth: { dev_login_enabled: true } }} />,
    );
    const link = await screen.findByRole("link", { name: /Continue as Neo/i });
    expect(link).toHaveAttribute("href", "/auth/dev/login?human=Neo&next=/app");
    expect(screen.getByText(/本地开发登录已开启/)).toBeInTheDocument();
  });
});
