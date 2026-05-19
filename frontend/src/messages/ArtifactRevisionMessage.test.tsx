import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { ArtifactRevisionMessage } from "./ArtifactRevisionMessage";

describe("<ArtifactRevisionMessage />", () => {
  it("renders artifact tag with version + thumbnails", () => {
    renderWithProviders(
      <ArtifactRevisionMessage
        actor={{ kind: "claude", initial: "CC", displayName: "claude" }}
        message={{
          id: 3, topic_id: 1, type: "artifact_revision", actor_type: "agent", actor_id: 11,
          body: "v0: 8 页骨架",
          metadata: { artifact_name: "ai-memory-talk.pptx", version: "v0" },
          ref_event_id: null, created_at: "2026-05-19T09:31:00Z",
        }}
      />,
    );
    expect(screen.getByText(/artifact_revision/)).toBeInTheDocument();
    expect(screen.getByText(/ai-memory-talk\.pptx/)).toBeInTheDocument();
    expect(screen.getAllByText(/v0/).length).toBeGreaterThan(0);
  });
});
