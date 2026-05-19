import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { ParticipantsPanel } from "./ParticipantsPanel";

describe("<ParticipantsPanel />", () => {
  it("renders each participant avatar", () => {
    renderWithProviders(
      <ParticipantsPanel
        participants={[
          { kind: "human", initial: "N", name: "Neo" },
          { kind: "claude", initial: "CC", name: "claude · neo-mbp" },
        ]}
      />,
    );
    expect(screen.getByTitle("Neo")).toBeInTheDocument();
    expect(screen.getByTitle("claude · neo-mbp")).toBeInTheDocument();
  });
});
