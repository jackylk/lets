import { describe, expect, it } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../test/render";
import { AgentDetail } from "./AgentDetail";

describe("<AgentDetail />", () => {
  it("updates the visible agent display name after saving", async () => {
    const user = userEvent.setup();
    renderWithProviders(<AgentDetail agentId={12} onBack={() => {}} />);

    expect(await screen.findByRole("heading", { name: "Trinity" })).toBeInTheDocument();

    const nameInput = screen.getByLabelText("展示名");
    await user.clear(nameInput);
    await user.type(nameInput, "Neo");
    await user.click(screen.getAllByRole("button", { name: "保存" })[0]!);

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Neo" })).toBeInTheDocument();
    });
  });

  it("lets a Claude agent model be changed to a full model name", async () => {
    const user = userEvent.setup();
    renderWithProviders(<AgentDetail agentId={11} onBack={() => {}} />);

    const modelInput = await screen.findByLabelText("模型");
    expect(modelInput).toHaveValue("haiku");

    await user.clear(modelInput);
    await user.type(modelInput, "sonnet-4.6");
    await user.click(screen.getAllByRole("button", { name: "保存" })[1]!);

    await waitFor(() => {
      expect(screen.getByText("sonnet-4.6")).toBeInTheDocument();
    });
  });
});
