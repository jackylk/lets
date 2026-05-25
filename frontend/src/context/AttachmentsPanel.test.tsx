import { describe, expect, it } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../test/render";
import { AttachmentsPanel } from "./AttachmentsPanel";

describe("<AttachmentsPanel />", () => {
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
});
