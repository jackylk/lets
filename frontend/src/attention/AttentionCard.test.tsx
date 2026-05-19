import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../test/render";
import { AttentionCard } from "./AttentionCard";

describe("<AttentionCard />", () => {
  it("renders who, what, topic ref, and fires action callbacks", async () => {
    const user = userEvent.setup();
    const onPrimary = vi.fn();
    const onSecondary = vi.fn();
    renderWithProviders(
      <AttentionCard
        avatar={{ kind: "claude", initial: "CC" }}
        whoLabel="claude · neo-mbp"
        timeIso="2026-05-19T10:32:00Z"
        what="framing 角度要不要更激进？"
        topicRef={{ id: "T-PPT", title: "为 Agent 记忆写一个研讨 PPT" }}
        primary={{ label: "采纳", onClick: onPrimary }}
        secondary={{ label: "先不", onClick: onSecondary }}
      />,
    );
    expect(screen.getByText(/framing/)).toBeInTheDocument();
    expect(screen.getByText("T-PPT")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "采纳" }));
    expect(onPrimary).toHaveBeenCalledTimes(1);
    await user.click(screen.getByRole("button", { name: "先不" }));
    expect(onSecondary).toHaveBeenCalledTimes(1);
  });
});
