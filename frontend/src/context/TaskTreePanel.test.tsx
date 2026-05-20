import { describe, it, expect } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../test/render";
import { TaskTreePanel } from "./TaskTreePanel";

describe("<TaskTreePanel />", () => {
  it("renders nested tree from useTopicTaskTree (fixture topic 1)", async () => {
    renderWithProviders(<TaskTreePanel topicId={1} />);
    await waitFor(() => {
      expect(screen.getByText(/Framing 角度定下来/)).toBeInTheDocument();
    });
    // The nested item under P5 is hidden by default (children collapsed)
    expect(screen.queryByText(/找去年反馈数据/)).not.toBeInTheDocument();
  });

  it("toggling expand shows nested children", async () => {
    const user = userEvent.setup();
    renderWithProviders(<TaskTreePanel topicId={1} />);
    await waitFor(() => screen.getByText(/P5 加文字解释/));
    const expandBtn = screen.getByRole("button", {
      name: /expand-5/i, // testid-style aria-label
    });
    await user.click(expandBtn);
    expect(screen.getByText(/找去年反馈数据/)).toBeInTheDocument();
  });

  it("checking a task marks it done", async () => {
    const user = userEvent.setup();
    renderWithProviders(<TaskTreePanel topicId={1} />);
    await waitFor(() => screen.getByText(/P5 加文字解释/));
    const cb = screen.getByRole("checkbox", { name: /P5 加文字解释/ });
    expect(cb).not.toBeChecked();
    await user.click(cb);
    await waitFor(() => expect(cb).toBeChecked());
  });

  it("can add a new task at root", async () => {
    const user = userEvent.setup();
    renderWithProviders(<TaskTreePanel topicId={1} />);
    await waitFor(() => screen.getByText(/Framing 角度定下来/));
    await user.click(screen.getByRole("button", { name: /\+ 加任务/i }));
    const input = screen.getByPlaceholderText(/输入新任务/i);
    await user.type(input, "新任务1{Enter}");
    await waitFor(() => expect(screen.getByText(/新任务1/)).toBeInTheDocument());
  });
});
