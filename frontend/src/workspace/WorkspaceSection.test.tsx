import { describe, it, expect, vi } from "vitest";
import { screen, fireEvent } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { WorkspaceSection } from "./WorkspaceSection";
import type { Workspace } from "../api/types";

const workspace: Workspace = {
  id: 2,
  name: "用户认证",
  slug: "user-auth",
  description: null,
  owner_human_id: 1,
  is_private: true,
  my_role: "member",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

describe("<WorkspaceSection />", () => {
  it("starts collapsed — shows workspace name but not topics", () => {
    renderWithProviders(
      <WorkspaceSection workspace={workspace} onSelectTopic={vi.fn()} />,
    );
    expect(screen.getByText("用户认证")).toBeInTheDocument();
    // The toggle arrow starts as ▸ (collapsed)
    expect(screen.getByText("▸")).toBeInTheDocument();
  });

  it("expands when clicked", () => {
    renderWithProviders(
      <WorkspaceSection workspace={workspace} onSelectTopic={vi.fn()} />,
    );
    const btn = screen.getByRole("button");
    fireEvent.click(btn);
    // After expand, shows ▾
    expect(screen.getByText("▾")).toBeInTheDocument();
  });
});
