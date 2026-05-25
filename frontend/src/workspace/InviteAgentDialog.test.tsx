import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
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
    expect(cmd.textContent).toBe("lets add claude --model haiku --workspace my-ws");
    const install = screen.getByTestId("invite-agent-install-command");
    expect(install.textContent).toContain(
      "/install | LETS_AGENT_ROLE=claude LETS_MODEL=haiku LETS_WORKSPACE=my-ws bash",
    );
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
    expect(cmd.textContent).toBe("lets add codex --model gpt-5.5 --workspace my-ws");
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

  it("copies install and add commands independently", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });
    render(
      <InviteAgentDialog
        workspaceName="我的工作区"
        workspaceSlug="my-ws"
        onClose={vi.fn()}
      />,
    );

    const copyButtons = screen.getAllByText("复制");
    expect(copyButtons).toHaveLength(2);
    fireEvent.click(copyButtons[0]!);
    await waitFor(() =>
      expect(writeText).toHaveBeenCalledWith(
        expect.stringContaining("LETS_AGENT_ROLE=claude LETS_MODEL=haiku LETS_WORKSPACE=my-ws bash"),
      ),
    );

    fireEvent.click(copyButtons[1]!);
    await waitFor(() =>
      expect(writeText).toHaveBeenCalledWith("lets add claude --model haiku --workspace my-ws"),
    );
  });
});
