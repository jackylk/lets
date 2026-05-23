import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { InviteDialog } from "./InviteDialog";

describe("InviteDialog", () => {
  it("renders join URL + copies on click", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });
    render(
      <InviteDialog
        workspaceName="我的工作区"
        joinUrl="https://lets.app/join/abc123"
        onClose={vi.fn()}
      />
    );
    expect(screen.getByDisplayValue("https://lets.app/join/abc123")).toBeInTheDocument();
    fireEvent.click(screen.getByText("复制"));
    await waitFor(() =>
      expect(writeText).toHaveBeenCalledWith("https://lets.app/join/abc123"),
    );
    expect(screen.getByText("已复制")).toBeInTheDocument();
  });

  it("falls back when clipboard permission is denied", async () => {
    const writeText = vi.fn().mockRejectedValue(new Error("denied"));
    Object.defineProperty(document, "execCommand", {
      configurable: true,
      value: vi.fn().mockReturnValue(true),
    });
    Object.assign(navigator, { clipboard: { writeText } });
    render(<InviteDialog workspaceName="X" joinUrl="https://x/y" onClose={vi.fn()} />);

    fireEvent.click(screen.getByText("复制"));

    await waitFor(() => expect(document.execCommand).toHaveBeenCalledWith("copy"));
    expect(screen.getByText("已复制")).toBeInTheDocument();
  });

  it("calls onClose when 完成 clicked", () => {
    const onClose = vi.fn();
    render(<InviteDialog workspaceName="X" joinUrl="https://x/y" onClose={onClose} />);
    fireEvent.click(screen.getByText("完成"));
    expect(onClose).toHaveBeenCalled();
  });
});
