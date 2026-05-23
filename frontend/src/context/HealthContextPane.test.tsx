import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { HealthContextPane, buildHealthContext, isHealthTopic } from "./HealthContextPane";
import type { MessageDTO } from "../api/types";

function msg(id: number, body: string): MessageDTO {
  return {
    id,
    topic_id: 1,
    type: "chat",
    actor_type: "human",
    actor_id: 1,
    body,
    metadata: {},
    ref_event_id: null,
    created_at: "2026-05-23T10:00:00Z",
  };
}

describe("health context pane", () => {
  it("detects health-related topics from symptoms or medication", () => {
    expect(isHealthTopic([msg(1, "我现在肚子疼，想问问怎么用药")])).toBe(true);
    expect(isHealthTopic([msg(2, "我们讨论一个文件检索工具")])).toBe(false);
  });

  it("extracts current situation, red flags, and medication mentions", () => {
    const ctx = buildHealthContext([
      msg(1, "我今天上腹胃疼，还有点发烧，吃了一片布洛芬。"),
    ]);

    expect(ctx.facts.some((f) => f.label === "疼痛位置" && f.value === "上腹")).toBe(true);
    expect(ctx.redFlags.find((f) => f.label === "发热或明显全身不适")?.matched).toBe(true);
    expect(ctx.medications.map((m) => m.name)).toContain("布洛芬");
    expect(ctx.suggestions.map((s) => s.title)).toContain("优先去医院 / 急诊");
  });

  it("renders a safety-oriented health pane", () => {
    render(
      <HealthContextPane
        messages={[msg(1, "我今天上腹胃疼，还有点发烧，吃了一片布洛芬。")]}
      />,
    );

    expect(screen.getByText(/健康求助模式/)).toBeInTheDocument();
    expect(screen.getByText("危险信号")).toBeInTheDocument();
    expect(screen.getByText("建议")).toBeInTheDocument();
    expect(screen.getByText("优先去医院 / 急诊")).toBeInTheDocument();
    expect(screen.getByText("用药记录")).toBeInTheDocument();
    expect(screen.getByText("布洛芬")).toBeInTheDocument();
    expect(screen.getByText(/不替代医生诊断/)).toBeInTheDocument();
  });

  it("shows medication and self-care suggestions when no red flag is mentioned", () => {
    render(
      <HealthContextPane
        messages={[msg(1, "我今天有点上腹胃疼，想看看能不能用药。")]}
      />,
    );

    expect(screen.getByText("可先做低风险护理")).toBeInTheDocument();
    expect(screen.getByText("像胃部不适时可问药师")).toBeInTheDocument();
    expect(screen.getByText("止痛/退热药要谨慎")).toBeInTheDocument();
  });
});
