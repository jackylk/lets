import { useState } from "react";
import { AppShell } from "./layout/AppShell";
import { Sidebar } from "./layout/Sidebar";
import { TopicView } from "./topic/TopicView";
import { TopicContext } from "./context/TopicContext";
import { AttentionView } from "./attention/AttentionView";
import { BottomTabs, type MobileTab } from "./layout/BottomTabs";

type DesktopView =
  | { kind: "topic"; id: number; title: string }
  | { kind: "attention" };

export default function App() {
  const [view, setView] = useState<DesktopView>({ kind: "topic", id: 1, title: "为 Agent 记忆写一个研讨 PPT" });
  const [mobileTab, setMobileTab] = useState<MobileTab>("topic");

  const isMobile =
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(max-width: 767px)").matches;

  const sidebar = (
    <Sidebar
      projectName="Lets"
      projectRepo="github.com/echomem/lets"
      attentionCount={4}
      onClickAttention={() => setView({ kind: "attention" })}
      onClickTopic={() => setView({ kind: "topic", id: 1, title: "为 Agent 记忆写一个研讨 PPT" })}
    />
  );

  let main: React.ReactNode;
  if (isMobile) {
    if (mobileTab === "topic") main = <TopicView topicId={1} topicTitle="为 Agent 记忆写一个研讨 PPT" />;
    else if (mobileTab === "attention") main = <AttentionView userName="Neo" />;
    else main = <TopicContext />;
  } else {
    main = view.kind === "topic"
      ? <TopicView topicId={view.id} topicTitle={view.title} />
      : <AttentionView userName="Neo" />;
  }

  return (
    <AppShell
      sidebar={sidebar}
      main={main}
      context={view.kind === "topic" ? <TopicContext /> : <div className="p-4 text-text-dim text-sm">No context</div>}
      bottomTabs={<BottomTabs active={mobileTab} onSelect={setMobileTab} />}
    />
  );
}
