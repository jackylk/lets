import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { SpecTouchedPanel } from "./SpecTouchedPanel";

describe("<SpecTouchedPanel />", () => {
  it("renders each spec path + current version", () => {
    renderWithProviders(
      <SpecTouchedPanel
        items={[
          { path: ".claude/skills/research-talk-style", version: "v2 → v3", pending: true },
          { path: ".claude/skills/pptx", version: "v5", pending: false },
        ]}
      />,
    );
    expect(screen.getByText(/research-talk-style/)).toBeInTheDocument();
    expect(screen.getByText(/v2 → v3/)).toBeInTheDocument();
    expect(screen.getByText(/pptx/)).toBeInTheDocument();
  });
});
