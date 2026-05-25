import { describe, expect, it } from "vitest";
import { makeActorResolver } from "./actorResolver";
import type { MessageDTO } from "../api/types";

const baseMessage: MessageDTO = {
  id: 1,
  topic_id: 1,
  type: "chat",
  actor_type: "agent",
  actor_id: 7,
  body: "old reply",
  metadata: {},
  ref_event_id: null,
  created_at: "2026-01-01T00:00:00Z",
};

describe("makeActorResolver", () => {
  it("marks deleted historical agents in display names", () => {
    const resolve = makeActorResolver({
      humans: [],
      agentInstances: [
        {
          id: 7,
          role: "codex",
          device_label: "mac16",
          display_name: "Neo",
          human_id: 1,
          deleted_at: "2026-05-25T00:00:00Z",
        },
      ],
    });

    expect(resolve(baseMessage).displayName).toBe("Neo (已移除)");
  });
});
