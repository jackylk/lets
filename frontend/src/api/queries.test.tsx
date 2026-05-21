import { describe, it, expect } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { useTopicMessages, useIdentityMe, useWorkspaces } from "./queries";

function Probe() {
  const me = useIdentityMe();
  const msgs = useTopicMessages(1);
  return (
    <>
      <span data-testid="me">{me.data?.human.name ?? "loading"}</span>
      <span data-testid="count">{msgs.data?.messages.length ?? -1}</span>
    </>
  );
}

function WorkspacesProbe() {
  const ws = useWorkspaces();
  return (
    <span data-testid="ws-count">
      {ws.isSuccess ? ws.data.length : -1}
    </span>
  );
}

describe("queries", () => {
  it("fetches identity and topic messages", async () => {
    renderWithProviders(<Probe />);
    await waitFor(() => expect(screen.getByTestId("me")).toHaveTextContent("Neo"));
    await waitFor(() => expect(screen.getByTestId("count")).toHaveTextContent("14"));
  });
});

describe("useWorkspaces", () => {
  it("returns workspaces list", async () => {
    renderWithProviders(<WorkspacesProbe />);
    await waitFor(() =>
      expect(screen.getByTestId("ws-count")).not.toHaveTextContent("-1"),
    );
    expect(screen.getByTestId("ws-count")).toHaveTextContent("1");
  });
});
