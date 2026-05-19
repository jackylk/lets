import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { TopicInfoCard } from "./TopicInfoCard";

describe("<TopicInfoCard />", () => {
  it("renders topic id, title, description, chips", () => {
    renderWithProviders(
      <TopicInfoCard
        topicSlug="T-PPT"
        title="为 Agent 记忆写一个研讨 PPT"
        description="下周三 AI 研讨会 30min talk"
        chips={["exploratory", "3 agents", "talk-prep"]}
      />,
    );
    expect(screen.getByText("T-PPT")).toBeInTheDocument();
    expect(screen.getByText(/30min talk/)).toBeInTheDocument();
    expect(screen.getByText("exploratory")).toBeInTheDocument();
    expect(screen.getByText("talk-prep")).toBeInTheDocument();
  });
});
