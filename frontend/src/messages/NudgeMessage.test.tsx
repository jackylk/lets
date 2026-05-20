import { describe, it, expect } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../test/render";
import { NudgeMessage } from "./NudgeMessage";

const sampleNudge = {
  id: 12, topic_id: 1, type: "nudge" as const,
  actor_type: "system" as const, actor_id: null,
  body: "这条线程已经讨论 framing 25 分钟，要不要先决定再继续？",
  metadata: { reason: "framing-loop", drift_summary: "discussing framing", drift_nudge_id: 1 },
  ref_event_id: null,
  created_at: "2026-05-19T10:50:00Z",
};

describe("<NudgeMessage />", () => {
  it("renders three quick-action buttons", () => {
    renderWithProviders(
      <NudgeMessage
        actor={{ kind: "system", initial: "S", displayName: "system" }}
        message={sampleNudge}
      />,
    );
    expect(screen.getByRole("button", { name: /独立成新 topic/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /回主线/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /略过/ })).toBeInTheDocument();
  });

  it("clicking 略过 dismisses the nudge", async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <NudgeMessage
        actor={{ kind: "system", initial: "S", displayName: "system" }}
        message={sampleNudge}
      />,
    );
    await user.click(screen.getByRole("button", { name: /略过/ }));
    await waitFor(() => {
      expect(screen.getByText(/已处理：略过/)).toBeInTheDocument();
    });
  });

  it("clicking 独立成新 topic opens spinoff dialog", async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <NudgeMessage
        actor={{ kind: "system", initial: "S", displayName: "system" }}
        message={sampleNudge}
      />,
    );
    await user.click(screen.getByRole("button", { name: /独立成新 topic/ }));
    await waitFor(() => {
      expect(screen.getByLabelText(/新 topic 标题/)).toBeInTheDocument();
    });
  });
});
