import { describe, it, expect } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { useTopicMessages, useIdentityMe } from "./queries";

function Probe() {
  const me = useIdentityMe();
  const msgs = useTopicMessages(1);
  return (
    <>
      <span data-testid="me">{me.data?.human.name ?? "loading"}</span>
      <span data-testid="count">{msgs.data?.length ?? -1}</span>
    </>
  );
}

describe("queries", () => {
  it("fetches identity and topic messages", async () => {
    renderWithProviders(<Probe />);
    await waitFor(() => expect(screen.getByTestId("me")).toHaveTextContent("Neo"));
    await waitFor(() => expect(screen.getByTestId("count")).toHaveTextContent("14"));
  });
});
