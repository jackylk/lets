import { describe, it, expect } from "vitest";
import { useTopicStream } from "./sse";

describe("useTopicStream", () => {
  it("module exports the hook", () => {
    expect(typeof useTopicStream).toBe("function");
  });
});
