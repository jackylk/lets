import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { InviteAgentDialog } from "./InviteAgentDialog";

describe("<InviteAgentDialog />", () => {
  it("renders the lets add command with the workspace slug", () => {
    render(
      <InviteAgentDialog
        workspaceName="我的工作区"
        workspaceSlug="my-ws"
        onClose={vi.fn()}
      />,
    );
    const cmd = screen.getByTestId("invite-agent-command");
    expect(cmd.textContent).toBe("lets add claude --workspace my-ws");
  });

  it("switches command when role is changed", () => {
    render(
      <InviteAgentDialog
        workspaceName="我的工作区"
        workspaceSlug="my-ws"
        onClose={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByRole("radio", { name: "Codex CLI" }));
    const cmd = screen.getByTestId("invite-agent-command");
    expect(cmd.textContent).toBe("lets add codex --workspace my-ws");
  });

  it("calls onClose when the done button is clicked", () => {
    const onClose = vi.fn();
    render(
      <InviteAgentDialog
        workspaceName="我的工作区"
        workspaceSlug="my-ws"
        onClose={onClose}
      />,
    );
    fireEvent.click(screen.getByText("完成"));
    expect(onClose).toHaveBeenCalledOnce();
  });
});
