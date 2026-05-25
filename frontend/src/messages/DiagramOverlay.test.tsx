import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DiagramOverlay } from "./DiagramOverlay";
import { openDiagram } from "./openDiagram";

function showDiagram() {
  render(<DiagramOverlay />);
  act(() => {
    openDiagram({
      source: "flowchart TD\nA[Start] --> B[End]",
      fromMsgId: 42,
      label: "flowchart td",
    });
  });
}

describe("<DiagramOverlay />", () => {
  it("closes when the user clicks outside the sheet", async () => {
    showDiagram();
    expect(await screen.findByRole("dialog", { name: "diagram preview" })).toBeInTheDocument();

    fireEvent.pointerDown(document.body);

    await waitFor(() => {
      expect(screen.queryByRole("dialog", { name: "diagram preview" })).toBeNull();
    });
  });

  it("stays open when the user clicks inside the sheet", async () => {
    showDiagram();
    const dialog = await screen.findByRole("dialog", { name: "diagram preview" });

    fireEvent.pointerDown(dialog);

    expect(screen.getByRole("dialog", { name: "diagram preview" })).toBeInTheDocument();
  });
});
