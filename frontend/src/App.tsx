import { AppShell } from "./layout/AppShell";
import { Sidebar } from "./layout/Sidebar";
import { TopicView } from "./topic/TopicView";

export default function App() {
  return (
    <AppShell
      sidebar={<Sidebar projectName="Lets" projectRepo="github.com/echomem/lets" attentionCount={4} />}
      main={<TopicView topicId={1} />}
      context={<div className="p-4 text-text-dim text-sm">Context pane (Phase 6)</div>}
    />
  );
}
