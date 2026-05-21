import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { InviteDialog } from "./InviteDialog";

describe("InviteDialog", () => {
  it("renders join URL + copies on click", async () => {
    const writeText = vi.fn();
    Object.assign(navigator, { clipboard: { writeText } });
    render(
      <InviteDialog
        workspaceName="我的工作区"
        joinUrl="https://lets.app/join/abc123"
        onClose={vi.fn()}
      />
    );
    expect(screen.getByText(/join\/abc123/)).toBeInTheDocument();
    fireEvent.click(screen.getByText("复制"));
    expect(writeText).toHaveBeenCalledWith("https://lets.app/join/abc123");
  });

  it("calls onClose when 完成 clicked", () => {
    const onClose = vi.fn();
    render(<InviteDialog workspaceName="X" joinUrl="https://x/y" onClose={onClose} />);
    fireEvent.click(screen.getByText("完成"));
    expect(onClose).toHaveBeenCalled();
  });
});
