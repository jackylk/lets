import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { ArtifactPanel } from "./ArtifactPanel";

describe("<ArtifactPanel />", () => {
  it("renders artifact name, version chip, thumbnails, version row", () => {
    renderWithProviders(
      <ArtifactPanel
        artifactName="ai-memory-talk.pptx"
        currentVersion="v2"
        versions={["v0", "v1", "v2"]}
        totalSlides={9}
      />,
    );
    expect(screen.getByText("ai-memory-talk.pptx")).toBeInTheDocument();
    expect(screen.getAllByText("v2").length).toBeGreaterThan(0);
    expect(screen.getByText(/\+ 5 页未显示/)).toBeInTheDocument();
  });
});
