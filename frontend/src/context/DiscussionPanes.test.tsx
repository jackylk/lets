import { describe, expect, it } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ConstraintsPanel, OptionsPanel } from "./DiscussionPanes";
import { renderWithProviders } from "../../test/render";

describe("discussion pane source labels", () => {
  it("marks agent-maintained context with a source pointer", () => {
    render(
      <OptionsPanel
        items={[
          {
            id: 20,
            kind: "option",
            title: "本地索引 MVP",
            body: "先做本地文件夹索引，再考虑云同步。",
            posted_by_agent: true,
            created_at: "2026-05-23T10:00:00Z",
            promoted_from: 12,
          },
        ]}
      />,
    );

    expect(screen.getByText("本地索引 MVP")).toBeInTheDocument();
    expect(screen.getByText("agent 总结 · 点击看来源 #12")).toBeInTheDocument();
  });

  it("distinguishes manually added context", () => {
    render(
      <ConstraintsPanel
        items={[
          {
            id: 21,
            kind: "constraint",
            body: "不能上传文件正文。",
            posted_by_agent: false,
            created_at: "2026-05-23T10:01:00Z",
            promoted_from: 21,
          },
        ]}
      />,
    );

    expect(screen.getByText("不能上传文件正文。")).toBeInTheDocument();
    expect(screen.getByText("人手动加入 · 点击看本条记录")).toBeInTheDocument();
  });

  it("lets people act on candidate options from the pane", async () => {
    renderWithProviders(
      <OptionsPanel
        topicId={1}
        items={[
          {
            id: 22,
            kind: "option",
            title: "本地索引 MVP",
            body: "先做本地文件夹索引。",
            posted_by_agent: true,
            created_at: "2026-05-23T10:02:00Z",
            promoted_from: 12,
          },
        ]}
      />,
    );

    const adopt = screen.getByText("采纳");
    await waitFor(() => expect(adopt).toBeEnabled());
    fireEvent.click(adopt);

    await waitFor(() => {
      expect(screen.getByText("已记为共识")).toBeInTheDocument();
    });
  });
});
