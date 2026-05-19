import { describe, it, expect, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../test/render";
import { IdentityProvider } from "./IdentityProvider";
import { useIdentity } from "./useIdentity";

function Probe() {
  const { humanName, setIdentity } = useIdentity();
  return (
    <>
      <span data-testid="who">{humanName ?? "anon"}</span>
      <button onClick={() => setIdentity({ humanName: "Neo" })}>set</button>
    </>
  );
}

describe("<IdentityProvider />", () => {
  beforeEach(() => localStorage.clear());

  it("starts anonymous and exposes setter", async () => {
    const user = userEvent.setup();
    renderWithProviders(<IdentityProvider><Probe /></IdentityProvider>);
    expect(screen.getByTestId("who")).toHaveTextContent("anon");
    await user.click(screen.getByText("set"));
    expect(screen.getByTestId("who")).toHaveTextContent("Neo");
  });

  it("persists across remount via localStorage", () => {
    localStorage.setItem(
      "lets.identity",
      JSON.stringify({ humanName: "Trinity", agentRole: null, deviceLabel: null }),
    );
    renderWithProviders(<IdentityProvider><Probe /></IdentityProvider>);
    expect(screen.getByTestId("who")).toHaveTextContent("Trinity");
  });
});
