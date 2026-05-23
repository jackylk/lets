import { useEffect, useMemo, useState } from "react";
import type { MessageDTO } from "../api/types";
import { isHealthTopic } from "./HealthContextPane";

export type TopicContextOverride = "auto" | "design" | "health";
export type TopicContextKind = "design" | "health";

function storageKey(topicId: number) {
  return `lets:topic-context-kind:${topicId}`;
}

function readOverride(topicId: number): TopicContextOverride {
  try {
    const raw = window.localStorage.getItem(storageKey(topicId));
    if (raw === "design" || raw === "health" || raw === "auto") return raw;
  } catch {
    /* ignore */
  }
  return "auto";
}

export function useTopicContextKind(
  topicId: number,
  messages: MessageDTO[],
  title = "",
): {
  detected: TopicContextKind;
  effective: TopicContextKind;
  override: TopicContextOverride;
  setOverride: (next: TopicContextOverride) => void;
} {
  const [override, setOverrideState] = useState<TopicContextOverride>(() => readOverride(topicId));

  useEffect(() => {
    setOverrideState(readOverride(topicId));
  }, [topicId]);

  const detected = useMemo<TopicContextKind>(
    () => (isHealthTopic(messages, title) ? "health" : "design"),
    [messages, title],
  );

  const effective = override === "auto" ? detected : override;

  function setOverride(next: TopicContextOverride) {
    setOverrideState(next);
    try {
      window.localStorage.setItem(storageKey(topicId), next);
    } catch {
      /* ignore */
    }
  }

  return { detected, effective, override, setOverride };
}
