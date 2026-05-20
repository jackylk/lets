import { describe, it, expect } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../test/render";
import { TaskTreePanel } from "./TaskTreePanel";

describe("<TaskTreePanel />", () => {
  it("renders an exploration tree with branch summaries", async () => {
    renderWithProviders(<TaskTreePanel topicId={1} />);
    await waitFor(() => {
      expect(screen.getByText("探索树")).toBeInTheDocument();
    });
    expect(screen.getByText(/Framing 角度定下来/)).toBeInTheDocument();
    expect(screen.getByText(/确定这次研讨 PPT/)).toBeInTheDocument();
    expect(screen.getByText(/P5 子任务/)).toBeInTheDocument();
  });

  it("cycles branch status", async () => {
    const user = userEvent.setup();
    renderWithProviders(<TaskTreePanel topicId={1} />);
    await waitFor(() => screen.getByText(/P5 加文字解释/));
    const status = screen.getAllByRole("button", { name: /待探索/ })[0]!;
    await user.click(status);
    await waitFor(() => expect(screen.getAllByRole("button", { name: /探索中/ }).length).toBeGreaterThan(0));
  });

  it("can add a root branch", async () => {
    const user = userEvent.setup();
    renderWithProviders(<TaskTreePanel topicId={1} />);
    await waitFor(() => screen.getByText(/Framing 角度定下来/));
    await user.click(screen.getByRole("button", { name: /\+ 添加方案分支/i }));
    await user.type(screen.getByPlaceholderText(/新方案分支/i), "新方向：生成式 UI");
    await user.type(screen.getByPlaceholderText(/目标、假设/i), "验证树状协作界面");
    await user.click(screen.getByRole("button", { name: /^添加$/ }));
    await waitFor(() => expect(screen.getByText(/新方向：生成式 UI/)).toBeInTheDocument());
    expect(screen.getByText(/验证树状协作界面/)).toBeInTheDocument();
  });

  it("can create an exploration tree when none exists", async () => {
    const user = userEvent.setup();
    renderWithProviders(<TaskTreePanel topicId={999} />);
    await waitFor(() => screen.getByText(/还没有探索树/));
    await user.click(screen.getByRole("button", { name: /创建探索树/ }));
    await waitFor(() => expect(screen.getByText("探索树")).toBeInTheDocument());
  });
});
