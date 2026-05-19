import { describe, it, expect } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { SessionGate } from "./SessionGate";

describe("<SessionGate />", () => {
  it("renders children when session is present (fixture defaults to Neo)", async () => {
    renderWithProviders(
      <SessionGate fallback={<div>locked</div>}>
        <div>secret area</div>
      </SessionGate>,
    );
    await waitFor(() => {
      expect(screen.getByText("secret area")).toBeInTheDocument();
    });
  });
});
