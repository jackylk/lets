import { useMemo } from "react";
import { useTopicMessages, usePostMessage, useIdentityMe } from "../api/queries";
import { useTopicStream } from "../api/sse";
import { TopicHeader } from "./TopicHeader";
import { Stream } from "./Stream";
import { Composer } from "./Composer";
import type { MessageDTO } from "../api/types";

interface Props {
  topicId: number;
  topicTitle: string;
}

const SCRATCH_DIRECTORY = {
  humans: [
    { id: 1, name: "Neo" },
    { id: 2, name: "Trinity" },
    { id: 3, name: "Morpheus" },
  ],
  agentInstances: [
    { id: 11, role: "claude", device_label: "neo-mbp", human_id: 1 },
    { id: 12, role: "claude", device_label: "trinity-air", human_id: 2 },
    { id: 13, role: "codex", device_label: "neo-mbp", human_id: 1 },
  ],
};

export function TopicView({ topicId, topicTitle }: Props) {
  const me = useIdentityMe();
  const initial = useTopicMessages(topicId);
  const live = useTopicStream(topicId);
  const postMessage = usePostMessage(topicId);

  const merged: MessageDTO[] = useMemo(() => {
    const base = initial.data?.messages ?? [];
    if (live.messages.length === 0) return base;
    const seen = new Set(base.map((m) => m.id));
    const extra = live.messages.filter((m) => !seen.has(m.id));
    return [...base, ...extra];
  }, [initial.data, live.messages]);

  function send(body: string) {
    if (!me.data) return;
    postMessage.mutate({
      topic_id: topicId,
      type: "chat",
      actor_type: "human",
      actor_id: me.data.human.id,
      body,
    });
  }

  return (
    <div className="flex flex-col h-full">
      <TopicHeader
        title={topicTitle}
        goal={{ doneCount: 3, totalCount: 7, currentTaskTitle: "P2 framing 改写" }}
      />
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {initial.isLoading && <div className="text-text-dim">加载中…</div>}
        {initial.isError && <div className="text-text-dim">加载失败</div>}
        <Stream messages={merged} directory={SCRATCH_DIRECTORY} />
      </div>
      <Composer onSend={send} disabled={postMessage.isPending} />
    </div>
  );
}
