import { AppShell } from "./layout/AppShell";
import { Sidebar } from "./layout/Sidebar";
import { TopicView } from "./topic/TopicView";
import { TopicContext } from "./context/TopicContext";

export default function App() {
  return (
    <AppShell
      sidebar={<Sidebar projectName="Lets" projectRepo="github.com/echomem/lets" attentionCount={4} />}
      main={<TopicView topicId={1} topicTitle="为 Agent 记忆写一个研讨 PPT" />}
      context={<TopicContext />}
    />
  );
}
