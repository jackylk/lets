import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { CreateWorkspaceInline } from "./CreateWorkspaceInline";

describe("<CreateWorkspaceInline />", () => {
  it("calls onSubmit with the typed name when Enter is pressed", () => {
    const onSubmit = vi.fn();
    render(<CreateWorkspaceInline onSubmit={onSubmit} onCancel={vi.fn()} />);
    const input = screen.getByRole("textbox");
    fireEvent.change(input, { target: { value: "新工作区" } });
    fireEvent.submit(input.closest("form")!);
    expect(onSubmit).toHaveBeenCalledWith("新工作区");
  });

  it("calls onCancel when Escape is pressed", () => {
    const onCancel = vi.fn();
    render(<CreateWorkspaceInline onSubmit={vi.fn()} onCancel={onCancel} />);
    const input = screen.getByRole("textbox");
    fireEvent.keyDown(input, { key: "Escape" });
    expect(onCancel).toHaveBeenCalledOnce();
  });

  it("does not submit when input is empty or whitespace-only", () => {
    const onSubmit = vi.fn();
    render(<CreateWorkspaceInline onSubmit={onSubmit} onCancel={vi.fn()} />);
    const input = screen.getByRole("textbox");
    fireEvent.change(input, { target: { value: "   " } });
    fireEvent.submit(input.closest("form")!);
    expect(onSubmit).not.toHaveBeenCalled();
  });
});
