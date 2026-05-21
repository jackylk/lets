import { expectTypeOf, test } from "vitest";
import type { MessageType, ActorType, MessageDTO, PostMessageInput } from "./types";

test("MessageType lists all 15 backend types", () => {
  expectTypeOf<MessageType>().toEqualTypeOf<
    | "chat" | "status" | "finding" | "decision" | "question"
    | "handoff" | "review" | "artifact_revision" | "spec_change"
    | "nudge" | "proactive_finding" | "task_tree_proposal"
    | "goal_proposal" | "system" | "annotation"
  >();
});
test("ActorType lists 3 actors", () => {
  expectTypeOf<ActorType>().toEqualTypeOf<"human" | "agent" | "system">();
});
test("MessageDTO has metadata as object", () => {
  expectTypeOf<MessageDTO["metadata"]>().toEqualTypeOf<Record<string, unknown>>();
});
test("PostMessageInput omits server-only fields", () => {
  expectTypeOf<PostMessageInput>().not.toHaveProperty("id");
  expectTypeOf<PostMessageInput>().not.toHaveProperty("created_at");
});
