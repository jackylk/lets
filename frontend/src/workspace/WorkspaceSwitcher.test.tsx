import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { WorkspaceSwitcher } from "./WorkspaceSwitcher";
import type { Workspace } from "../api/types";

const ws = (id: number, name: string): Workspace => ({
  id,
  name,
  slug: `ws-${id}`,
  description: null,
  owner_human_id: 1,
  is_private: true,
  my_role: "owner",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
});

describe("<WorkspaceSwitcher />", () => {
  it("calls onSelect when a chip is clicked", () => {
    const onSelect = vi.fn();
    render(
      <WorkspaceSwitcher
        workspaces={[ws(1, "我的工作区"), ws(2, "User Auth")]}
        activeId={1}
        onSelect={onSelect}
        onCreate={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByText("User Auth"));
    expect(onSelect).toHaveBeenCalledWith(2);
  });

  it("shows active workspace name", () => {
    render(
      <WorkspaceSwitcher
        workspaces={[ws(1, "我的工作区"), ws(2, "User Auth")]}
        activeId={1}
        onSelect={vi.fn()}
        onCreate={vi.fn()}
      />,
    );
    expect(screen.getByText(/我的工作区/)).toBeInTheDocument();
  });

  it("calls onCreate when + button clicked", () => {
    const onCreate = vi.fn();
    render(
      <WorkspaceSwitcher
        workspaces={[ws(1, "我的工作区")]}
        activeId={1}
        onSelect={vi.fn()}
        onCreate={onCreate}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "新建工作区" }));
    expect(onCreate).toHaveBeenCalledOnce();
  });

  it("shows up to 2 other workspaces as chips", () => {
    render(
      <WorkspaceSwitcher
        workspaces={[ws(1, "A"), ws(2, "B"), ws(3, "C"), ws(4, "D")]}
        activeId={1}
        onSelect={vi.fn()}
        onCreate={vi.fn()}
      />,
    );
    expect(screen.getByText("B")).toBeInTheDocument();
    expect(screen.getByText("C")).toBeInTheDocument();
    expect(screen.queryByText("D")).toBeNull();
  });
});
