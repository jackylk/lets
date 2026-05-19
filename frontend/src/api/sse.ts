import { useEffect, useState } from "react";
import type { MessageDTO } from "./types";

export interface UseTopicStreamResult {
  messages: MessageDTO[];
}

export function useTopicStream(topicId: number): UseTopicStreamResult {
  const [messages, setMessages] = useState<MessageDTO[]>([]);

  useEffect(() => {
    setMessages([]);
    // Skip live updates in fixture mode (MSW can't simulate persistent SSE).
    if (import.meta.env.VITE_USE_FIXTURES !== "false") return;

    const es = new EventSource(`/api/topics/${topicId}/stream`);
    es.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data) as MessageDTO;
        setMessages((prev) => [...prev, data]);
      } catch {
        /* ignore malformed */
      }
    };
    es.onerror = () => es.close();
    return () => es.close();
  }, [topicId]);

  return { messages };
}
