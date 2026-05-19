import { useState } from "react";
import { AppShell } from "./layout/AppShell";
import { Sidebar } from "./layout/Sidebar";
import { TopicView } from "./topic/TopicView";
import { TopicContext } from "./context/TopicContext";
import { AttentionView } from "./attention/AttentionView";

type View = { kind: "topic"; id: number; title: string } | { kind: "attention" };

export default function App() {
  const [view, setView] = useState<View>({ kind: "topic", id: 1, title: "为 Agent 记忆写一个研讨 PPT" });

  return (
    <AppShell
      sidebar={
        <Sidebar
          projectName="Lets"
          projectRepo="github.com/echomem/lets"
          attentionCount={4}
          onClickAttention={() => setView({ kind: "attention" })}
          onClickTopic={() => setView({ kind: "topic", id: 1, title: "为 Agent 记忆写一个研讨 PPT" })}
        />
      }
      main={
        view.kind === "topic" ? (
          <TopicView topicId={view.id} topicTitle={view.title} />
        ) : (
          <AttentionView userName="Neo" />
        )
      }
      context={view.kind === "topic" ? <TopicContext /> : <div className="p-4 text-text-dim text-sm">No context</div>}
    />
  );
}
