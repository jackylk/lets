import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { MoveTopicMenu } from "./MoveTopicMenu";

const wsFixture = (id: number, name: string) => ({
  id, name, slug: `ws-${id}`, description: null, owner_human_id: 1,
  is_private: true, my_role: "owner" as const,
  created_at: "", updated_at: "",
});

describe("MoveTopicMenu", () => {
  it("lists destination workspaces (excluding current) and triggers onMove", () => {
    const onMove = vi.fn();
    render(
      <MoveTopicMenu
        currentWorkspaceId={1}
        workspaces={[wsFixture(1, "A"), wsFixture(2, "B"), wsFixture(3, "C")]}
        onMove={onMove}
      />
    );
    expect(screen.queryByText("A")).toBeNull();
    fireEvent.click(screen.getByText("B"));
    expect(onMove).toHaveBeenCalledWith(2);
  });

  it("shows empty state when no other workspaces", () => {
    render(
      <MoveTopicMenu
        currentWorkspaceId={1}
        workspaces={[wsFixture(1, "A")]}
        onMove={vi.fn()}
      />
    );
    expect(screen.getByText(/没有其他工作区/)).toBeInTheDocument();
  });
});
