import { useCallback, useEffect, useState } from "react";

/**
 * Per-topic, per-device dismissal of open_questions the human doesn't want
 * to engage with. Lives in localStorage — not synced to the blackboard,
 * because the goal is "get this out of my way" (a private UI affordance),
 * not "tell everyone I chose to ignore it". Agents see no signal from this.
 *
 * Storage key: `lets:dismissed-questions:<topicId>` → JSON array of ids.
 */

function storageKey(topicId: number): string {
  return `lets:dismissed-questions:${topicId}`;
}

function readSet(topicId: number): Set<number> {
  if (typeof window === "undefined") return new Set();
  try {
    const raw = window.localStorage.getItem(storageKey(topicId));
    if (!raw) return new Set();
    const arr = JSON.parse(raw);
    if (!Array.isArray(arr)) return new Set();
    return new Set(arr.filter((x): x is number => typeof x === "number"));
  } catch {
    return new Set();
  }
}

function writeSet(topicId: number, set: Set<number>): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(storageKey(topicId), JSON.stringify([...set]));
  } catch {
    /* quota exceeded etc. — fine to silently drop */
  }
}

export function useDismissedQuestions(topicId: number): {
  dismissed: Set<number>;
  dismiss: (qid: number) => void;
  restoreAll: () => void;
} {
  const [dismissed, setDismissed] = useState<Set<number>>(() => readSet(topicId));

  useEffect(() => {
    setDismissed(readSet(topicId));
  }, [topicId]);

  const dismiss = useCallback(
    (qid: number) => {
      setDismissed((prev) => {
        if (prev.has(qid)) return prev;
        const next = new Set(prev);
        next.add(qid);
        writeSet(topicId, next);
        return next;
      });
    },
    [topicId],
  );

  const restoreAll = useCallback(() => {
    setDismissed(() => {
      writeSet(topicId, new Set());
      return new Set();
    });
  }, [topicId]);

  return { dismissed, dismiss, restoreAll };
}
