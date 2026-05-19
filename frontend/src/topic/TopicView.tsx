import { useTopicMessages } from "../api/queries";
import { TopicHeader } from "./TopicHeader";
import { Stream } from "./Stream";

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
  const { data, isLoading, isError } = useTopicMessages(topicId);

  return (
    <div className="flex flex-col h-full">
      <TopicHeader
        title={topicTitle}
        goal={{ doneCount: 3, totalCount: 7, currentTaskTitle: "P2 framing 改写" }}
      />
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {isLoading && <div className="text-text-dim">加载中…</div>}
        {isError && <div className="text-text-dim">加载失败</div>}
        {data && <Stream messages={data} directory={SCRATCH_DIRECTORY} />}
      </div>
    </div>
  );
}
