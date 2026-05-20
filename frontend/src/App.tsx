import { useEffect, useState } from "react";
import { AppShell } from "./layout/AppShell";
import { Sidebar } from "./layout/Sidebar";
import { TopicView } from "./topic/TopicView";
import { TopicContext } from "./context/TopicContext";
import { AttentionView } from "./attention/AttentionView";
import { BottomTabs, type MobileTab } from "./layout/BottomTabs";
import { SessionGate } from "./auth/SessionGate";
import { LoginPage } from "./auth/LoginPage";
import { SettingsTokensPage } from "./settings/SettingsTokensPage";
import {
  useProjects, useProject, useProjectTopics, useAttention, useSessionMe,
} from "./api/queries";

type DesktopView =
  | { kind: "topic"; id: number }
  | { kind: "attention" }
  | { kind: "settings-tokens" };

export default function App() {
  return (
    <SessionGate fallback={<LoginPage />}>
      <Workspace />
    </SessionGate>
  );
}

function Workspace() {
  // Fetch projects; default to first project. Single-user mode = single
  // project most of the time, so we don't bother with a switcher UI yet.
  const projects = useProjects();
  const [projectId, setProjectId] = useState<number | null>(null);
  useEffect(() => {
    if (projectId === null && projects.data && projects.data.length > 0) {
      // Prefer the project whose slug doesn't equal 'default' if available
      const real = projects.data.find((p) => p.slug !== "default") ?? projects.data[0];
      if (real) setProjectId(real.id);
    }
  }, [projects.data, projectId]);

  const project = useProject(projectId);
  const topics = useProjectTopics(projectId);
  const session = useSessionMe();
  const attention = useAttention(session.data?.human.id ?? null);

  const [topicId, setTopicId] = useState<number | null>(null);
  useEffect(() => {
    if (topicId === null && topics.data && topics.data.length > 0) {
      // Pick the most recently-created topic (last in id order)
      const t = [...topics.data].sort((a, b) => b.id - a.id)[0];
      if (t) setTopicId(t.id);
    }
  }, [topics.data, topicId]);

  const [view, setView] = useState<DesktopView>({ kind: "topic", id: 0 });
  useEffect(() => {
    if (topicId !== null && view.kind === "topic" && view.id === 0) {
      setView({ kind: "topic", id: topicId });
    }
  }, [topicId, view]);
  const [mobileTab, setMobileTab] = useState<MobileTab>("topic");

  const isMobile =
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(max-width: 767px)").matches;

  const sidebar = (
    <Sidebar
      projectName={project.data?.name ?? "Lets"}
      projectRepo={project.data?.repo_path ?? project.data?.slug ?? ""}
      topics={topics.data ?? []}
      activeTopicId={view.kind === "topic" ? view.id : null}
      attentionCount={
        attention.data
          ? attention.data.needs_decision.length +
            attention.data.mentioned_questions.length +
            attention.data.suggestions.length
          : 0
      }
      onClickAttention={() => setView({ kind: "attention" })}
      onSelectTopic={(id) => setView({ kind: "topic", id })}
      onClickSettings={() => setView({ kind: "settings-tokens" })}
    />
  );

  const activeTopicId = view.kind === "topic" && view.id > 0 ? view.id : topicId;
  const userName = session.data?.human.name ?? "you";

  let main: React.ReactNode;
  if (isMobile) {
    if (mobileTab === "topic" && activeTopicId)
      main = <TopicView topicId={activeTopicId} />;
    else if (mobileTab === "attention") main = <AttentionView userName={userName} />;
    else if (activeTopicId)
      main = <TopicContext topicId={activeTopicId} projectId={projectId} />;
    else main = <div className="p-6 text-text-dim">No topic selected</div>;
  } else if (view.kind === "topic" && view.id > 0) {
    main = <TopicView topicId={view.id} />;
  } else if (view.kind === "attention") {
    main = <AttentionView userName={userName} />;
  } else if (view.kind === "settings-tokens") {
    main = <SettingsTokensPage />;
  } else {
    main = (
      <div className="p-6 text-text-dim">
        {projects.isLoading || topics.isLoading
          ? "加载中…"
          : "尚无 topic — 在 Settings 创建第一个 project + topic"}
      </div>
    );
  }

  const context =
    view.kind === "topic" && activeTopicId ? (
      <TopicContext topicId={activeTopicId} projectId={projectId} />
    ) : (
      <div className="p-4 text-text-dim text-sm">No context</div>
    );

  return (
    <AppShell
      sidebar={sidebar}
      main={main}
      context={context}
      bottomTabs={<BottomTabs active={mobileTab} onSelect={setMobileTab} />}
    />
  );
}
