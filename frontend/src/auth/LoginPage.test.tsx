import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { LoginPage } from "./LoginPage";

describe("<LoginPage />", () => {
  it("renders Login with GitHub button pointing to /auth/github/start", () => {
    renderWithProviders(<LoginPage />);
    const link = screen.getByRole("link", { name: /Login with GitHub/i });
    expect(link).toHaveAttribute("href", "/auth/github/start");
  });
});
