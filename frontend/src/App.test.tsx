import { describe, it, expect } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { renderWithProviders } from "../test/render";
import App from "./App";
import { server } from "./fixtures/server";

describe("<App />", () => {
  it("renders the topic title in the header once data loads", async () => {
    renderWithProviders(<App />);
    await waitFor(
      () => {
        expect(screen.getByRole("heading", { name: /PPT/ })).toBeInTheDocument();
      },
      { timeout: 5000 },
    );
  });

  it("renders the public home page when not logged in", async () => {
    server.use(http.get("/auth/me", () => new HttpResponse(null, { status: 401 })));
    renderWithProviders(<App />);
    await waitFor(
      () =>
        expect(
          screen.getByRole("heading", { name: "把讨论变成可持续推进的协作动作" }),
        ).toBeInTheDocument(),
      { timeout: 5000 },
    );
  });
});
