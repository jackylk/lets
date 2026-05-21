import { useEffect, useState } from "react";
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
  useWorkspaces, useTopicsInWorkspace, useWorkspaceMembers,
  useCreateWorkspace, useAttention, useSessionMe, useAllAgents,
} from "./api/queries";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "./api/client";
import { useIdentity } from "./identity/useIdentity";
import type { TopicDTO, Workspace } from "./api/types";

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
  // Fetch workspaces; default to first workspace
  const workspacesQuery = useWorkspaces();
  const workspaces = workspacesQuery.data ?? [];

  const [activeWorkspaceId, setActiveWorkspaceId] = useState<number | null>(null);

  useEffect(() => {
    if (activeWorkspaceId === null && workspaces.length > 0) {
      const first = workspaces[0];
      if (first) setActiveWorkspaceId(first.id);
    }
  }, [workspaces, activeWorkspaceId]);

  const activeWorkspace: Workspace | undefined = workspaces.find(
    (w) => w.id === activeWorkspaceId,
  );

  const topicsQuery = useTopicsInWorkspace(activeWorkspaceId);
  const topics = topicsQuery.data ?? [];

  const membersQuery = useWorkspaceMembers(activeWorkspaceId);
  const members = membersQuery.data ?? [];

  const session = useSessionMe();
  const attention = useAttention(session.data?.human.id ?? null);
  const allAgents = useAllAgents();

  const [topicId, setTopicId] = useState<number | null>(null);
  useEffect(() => {
    if (topicId === null && topics.length > 0) {
      const t = [...topics].sort((a, b) => b.id - a.id)[0];
      if (t) setTopicId(t.id);
    }
  }, [topics, topicId]);

  // Reset topicId when switching workspaces so we re-select from new topic list
  const handleSwitchWorkspace = (id: number) => {
    setActiveWorkspaceId(id);
    setTopicId(null);
    setView({ kind: "topic", id: 0 });
  };

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
      apiRequest<TopicDTO>(`/api/workspaces/${activeWorkspaceId}/topics`, {
        method: "POST", body: input, identity,
      }),
    onSuccess: (created) => {
      qc.invalidateQueries({ queryKey: ["workspace-topics", activeWorkspaceId] });
      setView({ kind: "topic", id: created.id });
      setTopicId(created.id);
    },
  });

  const createWorkspace = useCreateWorkspace();

  const handleCreateWorkspace = (name: string) => {
    createWorkspace.mutate(name, {
      onSuccess: (ws) => {
        setActiveWorkspaceId(ws.id);
        setTopicId(null);
        setView({ kind: "topic", id: 0 });
      },
    });
  };

  const handleInviteMember = () => {
    // Task 15 builds InviteDialog — placeholder for now
    console.log("invite TODO");
  };

  const sidebar = (
    <Sidebar
      activeWorkspace={activeWorkspace}
      workspaces={workspaces}
      topics={topics}
      members={members}
      activeTopicId={view.kind === "topic" ? view.id : null}
      onSelectTopic={(id) => setView({ kind: "topic", id })}
      onCreateTopic={
        activeWorkspaceId === null
          ? () => {}
          : async (input) => {
              await createTopic.mutateAsync(input);
            }
      }
      onSwitchWorkspace={handleSwitchWorkspace}
      onCreateWorkspace={handleCreateWorkspace}
      onInviteMember={handleInviteMember}
      onClickSettings={() => setView({ kind: "settings-tokens" })}
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
      main = <TopicContext topicId={activeTopicId} projectId={activeWorkspaceId} />;
    else main = <div className="p-6 text-text-dim">加载中…</div>;
  } else if (view.kind === "topic" && view.id > 0) {
    main = topicMain(view.id);
  } else if (view.kind === "attention") {
    main = <AttentionView userName={userName} />;
  } else if (view.kind === "settings-tokens") {
    main = <SettingsTokensPage />;
  } else {
    main = <div className="p-6 text-text-dim">加载中…</div>;
  }

  const context =
    view.kind === "topic" && activeTopicId ? (
      <TopicContext topicId={activeTopicId} projectId={activeWorkspaceId} />
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
