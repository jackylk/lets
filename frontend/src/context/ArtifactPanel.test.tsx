import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { ArtifactPanel } from "./ArtifactPanel";
import type { ArtifactDTO } from "../api/types";

const sample: ArtifactDTO = {
  id: 1,
  slug: "ai-memory-talk.pptx",
  type: "doc",
  backend: "git",
  backend_ref: "ai-memory-talk.pptx",
  title: "AI memory talk",
  topic_id: 1,
  current_version_id: 3,
  versions: [
    {
      id: 1, artifact_id: 1, version_label: "v0",
      backend_revision_id: "abcd1234567890",
      summary: "initial",
      preview_uri: null,
      created_at: "2026-05-19T09:31:00Z",
    },
    {
      id: 2, artifact_id: 1, version_label: "v1",
      backend_revision_id: "efgh1234567890",
      summary: "tweaks",
      preview_uri: null,
      created_at: "2026-05-19T09:40:00Z",
    },
    {
      id: 3, artifact_id: 1, version_label: "v2",
      backend_revision_id: "ijkl1234567890",
      summary: "ship",
      preview_uri: null,
      created_at: "2026-05-19T10:00:00Z",
    },
  ],
};

describe("<ArtifactPanel />", () => {
  it("renders slug, current version, and the version chain", () => {
    renderWithProviders(<ArtifactPanel artifacts={[sample]} />);
    expect(screen.getByText("ai-memory-talk.pptx")).toBeInTheDocument();
    expect(screen.getAllByText("v2").length).toBeGreaterThan(0);
    expect(screen.getByText("v0")).toBeInTheDocument();
    expect(screen.getByText("v1")).toBeInTheDocument();
  });
});
