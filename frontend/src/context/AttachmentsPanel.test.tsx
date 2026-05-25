import { afterEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../test/render";
import { AttachmentsPanel } from "./AttachmentsPanel";

describe("<AttachmentsPanel />", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    delete (URL as unknown as { createObjectURL?: unknown }).createObjectURL;
    delete (URL as unknown as { revokeObjectURL?: unknown }).revokeObjectURL;
  });

  it("uploads a file into the topic attachment list", async () => {
    const user = userEvent.setup();
    renderWithProviders(<AttachmentsPanel topicId={1} />);

    await screen.findByText("还没有共享文件。");

    const file = new File(["hello"], "notes.txt", { type: "text/plain" });
    await user.upload(screen.getByLabelText("选择共享文件"), file);

    await waitFor(() => {
      expect(screen.getByText("文件 · notes.txt")).toBeInTheDocument();
    });
    expect(screen.getByText("5 B · text/plain")).toBeInTheDocument();
  });

  it("opens image attachments in a side preview", async () => {
    const createObjectURL = vi.fn(() => "blob:mock-image");
    const revokeObjectURL = vi.fn();
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      value: createObjectURL,
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      value: revokeObjectURL,
    });
    const user = userEvent.setup();
    renderWithProviders(<AttachmentsPanel topicId={1} />);

    await screen.findByText("还没有共享文件。");

    const file = new File(["gif"], "0.gif", { type: "image/gif" });
    await user.upload(screen.getByLabelText("选择共享文件"), file);
    await screen.findByText("图片 · 0.gif");

    await user.click(screen.getByRole("button", { name: "查看" }));

    const preview = await screen.findByRole("dialog", { name: "查看图片 0.gif" });
    expect(preview).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "0.gif" })).toHaveAttribute("src", "blob:mock-image");
    expect(createObjectURL).toHaveBeenCalledTimes(1);

    await user.click(screen.getByRole("button", { name: "关闭图片预览" }));

    await waitFor(() => {
      expect(screen.queryByRole("dialog", { name: "查看图片 0.gif" })).not.toBeInTheDocument();
    });
  });
});
