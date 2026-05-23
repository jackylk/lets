import { describe, expect, it } from "vitest";
import { summarizeTopicGoal, summarizeTopicIntent } from "./intentSummary";

describe("intent summary", () => {
  it("summarizes a discussion opener into a compact topic title", () => {
    expect(
      summarizeTopicIntent("有人在吗？我想讨论一个支持自然语言的文件检索工具"),
    ).toBe("自然语言文件检索工具");
  });

  it("summarizes inferred goal instead of copying the first sentence", () => {
    expect(
      summarizeTopicGoal("有人在吗？我想讨论一个支持自然语言的文件检索工具"),
    ).toBe("讨论并设计「自然语言文件检索工具」的目标、方案和风险");
  });
});
