import { useTopicMessages } from "../api/queries";
import { TopicHeader } from "./TopicHeader";
import { DaySeparator } from "./DaySeparator";

interface Props { topicId: number }

export function TopicView({ topicId }: Props) {
  const { data, isLoading, isError } = useTopicMessages(topicId);

  return (
    <div className="flex flex-col h-full">
      <TopicHeader
        title="为 Agent 记忆写一个研讨 PPT"
        goal={{ doneCount: 3, totalCount: 7, currentTaskTitle: "P2 framing 改写" }}
      />
      <div className="flex-1 overflow-y-auto px-6 py-4">
        <DaySeparator label="今天" />
        {isLoading && <div className="text-text-dim">加载中…</div>}
        {isError && <div className="text-text-dim">加载失败</div>}
        {data?.map((m) => (
          <div key={m.id} data-testid="message-row" className="py-2 border-b border-border-soft">
            <div className="text-[11px] font-mono text-text-dim">
              {m.type} · actor {m.actor_type}#{m.actor_id ?? "-"}
            </div>
            <div>{m.body}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
