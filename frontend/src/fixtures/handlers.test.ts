import { describe, it, expect } from "vitest";

describe("MSW handlers", () => {
  it("returns 14 messages for topic 1", async () => {
    const res = await fetch("/api/topics/1/messages");
    const data = (await res.json()) as { messages: unknown[]; drift_context: unknown };
    expect(data.messages).toHaveLength(14);
    expect(data.drift_context).toBeDefined();
  });

  it("returns identity for header-named human", async () => {
    const res = await fetch("/api/identity/me", { headers: { "X-Lets-Human": "Trinity" } });
    const data = (await res.json()) as { human: { name: string } };
    expect(data.human.name).toBe("Trinity");
  });

  it("filters messages by type", async () => {
    const res = await fetch("/api/topics/1/messages?type=spec_change");
    const data = (await res.json()) as { messages: unknown[] };
    expect(data.messages).toHaveLength(1);
  });
});
