import { useEffect, useRef, useState } from "react";
import { AppShell } from "./layout/AppShell";
import { Sidebar } from "./layout/Sidebar";
import { SidebarRail } from "./layout/SidebarRail";
import { TopicView } from "./topic/TopicView";
import { TopicContext } from "./context/TopicContext";
import { AttentionView } from "./attention/AttentionView";
import { BottomTabs, type MobileTab } from "./layout/BottomTabs";
import { SessionGate } from "./auth/SessionGate";
import { LoginPage } from "./auth/LoginPage";
import { SettingsTokensPage } from "./settings/SettingsTokensPage";
import {
  ConnectComputerBanner,
  isConnectBannerDismissed,
} from "./onboarding/ConnectComputerCard";
import {
  useProjects, useProjectTopics, useAttention, useSessionMe,
  useAllAgents,
} from "./api/queries";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "./api/client";
import { useIdentity } from "./identity/useIdentity";
import type { TopicDTO } from "./api/types";

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

  const topics = useProjectTopics(projectId);
  const session = useSessionMe();
  const attention = useAttention(session.data?.human.id ?? null);
  const allAgents = useAllAgents();

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

  const identity = useIdentity();
  const qc = useQueryClient();
  const createTopic = useMutation({
    mutationFn: (input: { slug: string; title: string }) =>
      apiRequest<TopicDTO>(`/api/projects/${projectId}/topics`, {
        method: "POST", body: input, identity,
      }),
    onSuccess: (created) => {
      qc.invalidateQueries({ queryKey: ["projects", projectId, "topics"] });
      setView({ kind: "topic", id: created.id });
      setTopicId(created.id);
    },
  });

  // First-run onboarding: if the user has a project but zero topics, mint a
  // default chat so the post-login first impression is the composer, not an
  // empty state. Guarded with a ref so React strict-mode double-effects don't
  // create duplicates.
  const autoTopicAttempted = useRef(false);
  useEffect(() => {
    if (
      !autoTopicAttempted.current &&
      projectId !== null &&
      !topics.isLoading &&
      (topics.data?.length ?? 0) === 0 &&
      !createTopic.isPending
    ) {
      autoTopicAttempted.current = true;
      createTopic.mutate({
        slug: `general-${Date.now().toString(36)}`,
        title: "主频道",
      });
    }
  }, [projectId, topics.data, topics.isLoading, createTopic]);

  const sidebar = (
    <Sidebar
      topics={topics.data ?? []}
      activeTopicId={view.kind === "topic" ? view.id : null}
      onSelectTopic={(id) => setView({ kind: "topic", id })}
      onClickSettings={() => setView({ kind: "settings-tokens" })}
      onCreateTopic={
        projectId === null
          ? undefined
          : async (input) => {
              await createTopic.mutateAsync(input);
            }
      }
    />
  );

  const activeTopicId = view.kind === "topic" && view.id > 0 ? view.id : topicId;
  const userName = session.data?.human.name ?? "you";
  const noAgents = !allAgents.isLoading && (allAgents.data?.length ?? 0) === 0;
  const [bannerDismissed, setBannerDismissed] = useState(isConnectBannerDismissed);
  const showInstallBanner = noAgents && !bannerDismissed;

  const topicMain = (id: number) => (
    <div className="flex flex-col h-full min-h-0">
      {showInstallBanner && (
        <ConnectComputerBanner onDismiss={() => setBannerDismissed(true)} />
      )}
      <div className="flex-1 min-h-0">
        <TopicView topicId={id} />
      </div>
    </div>
  );

  let main: React.ReactNode;
  if (isMobile) {
    if (mobileTab === "topic" && activeTopicId)
      main = topicMain(activeTopicId);
    else if (mobileTab === "attention") main = <AttentionView userName={userName} />;
    else if (activeTopicId)
      main = <TopicContext topicId={activeTopicId} projectId={projectId} />;
    else main = <div className="p-6 text-text-dim">加载中…</div>;
  } else if (view.kind === "topic" && view.id > 0) {
    main = topicMain(view.id);
  } else if (view.kind === "attention") {
    main = <AttentionView userName={userName} />;
  } else if (view.kind === "settings-tokens") {
    main = <SettingsTokensPage />;
  } else {
    // First-load / between auto-topic creation and routing into it.
    main = <div className="p-6 text-text-dim">加载中…</div>;
  }

  const context =
    view.kind === "topic" && activeTopicId ? (
      <TopicContext topicId={activeTopicId} projectId={projectId} />
    ) : (
      <div className="p-4 text-text-dim text-sm">No context</div>
    );

  const sidebarRail = (
    <SidebarRail
      attentionCount={
        attention.data
          ? attention.data.needs_decision.length +
            attention.data.mentioned_questions.length +
            attention.data.suggestions.length
          : 0
      }
      onClickAttention={() => setView({ kind: "attention" })}
      onClickSettings={() => setView({ kind: "settings-tokens" })}
    />
  );

  return (
    <AppShell
      sidebar={sidebar}
      sidebarRail={sidebarRail}
      main={main}
      context={context}
      bottomTabs={<BottomTabs active={mobileTab} onSelect={setMobileTab} />}
    />
  );
}
