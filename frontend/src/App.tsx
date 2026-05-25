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
import { HomePage } from "./home/HomePage";
import {
  useWorkspaces, useTopicsInWorkspace, useWorkspaceMembers,
  useCreateWorkspace, useAttention, useSessionMe,
  useCreateInvite, useRenameWorkspace, useDeleteWorkspace, useRenameTopic,
  useArchiveTopic, useRestoreTopic, useDeleteTopic,
  useRemoveWorkspaceMember, useRemoveWorkspaceAgent,
} from "./api/queries";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "./api/client";
import { useIdentity } from "./identity/useIdentity";
import type { TopicDTO, Workspace, WorkspaceInvite } from "./api/types";
import { InviteDialog } from "./workspace/InviteDialog";
import { InviteAgentDialog } from "./workspace/InviteAgentDialog";
import { JoinTokenPage } from "./join/JoinTokenPage";
import { AgentDetail } from "./agent/AgentDetail";
import { AgentList } from "./agent/AgentList";

type DesktopView =
  | { kind: "topic"; id: number }
  | { kind: "attention" }
  | { kind: "settings-tokens" }
  | { kind: "agents" }
  | { kind: "agent-detail"; id: number };

export default function App() {
  const path = typeof window !== "undefined" ? window.location.pathname : "/";

  if (path.startsWith("/join/")) {
    const token = path.slice("/join/".length);
    return <JoinTokenPage token={token} />;
  }

  if (path === "" || path === "/") {
    return (
      <SessionGate fallback={<HomePage />}>
        <Workspace />
      </SessionGate>
    );
  }

  return <SessionGate fallback={<LoginPage />}><Workspace /></SessionGate>;
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

  const topicsQuery = useTopicsInWorkspace(activeWorkspaceId, false, "mine");
  const topics = topicsQuery.data ?? [];
  const allTopicsQuery = useTopicsInWorkspace(activeWorkspaceId, false, "all");
  const allTopics = allTopicsQuery.data ?? [];
  const archivedTopicsQuery = useTopicsInWorkspace(activeWorkspaceId, true, "mine");
  const archivedTopics = archivedTopicsQuery.data ?? [];

  const membersQuery = useWorkspaceMembers(activeWorkspaceId);
  const members = membersQuery.data ?? [];

  const session = useSessionMe();
  const attention = useAttention(session.data?.human.id ?? null);

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
  const [mobileBoardOpen, setMobileBoardOpen] = useState(false);
  const isMobile = useMediaQuery("(max-width: 767px)");

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
      if (isMobile) setMobileTab("topic");
    },
  });

  const createWorkspace = useCreateWorkspace();
  const renameWorkspace = useRenameWorkspace();
  const deleteWorkspace = useDeleteWorkspace();
  const renameTopic = useRenameTopic();
  const archiveTopic = useArchiveTopic();
  const restoreTopic = useRestoreTopic();
  const deleteTopic = useDeleteTopic();
  const removeWorkspaceMember = useRemoveWorkspaceMember(activeWorkspaceId);
  const removeWorkspaceAgent = useRemoveWorkspaceAgent(activeWorkspaceId);

  const handleCreateWorkspace = (name: string) => {
    createWorkspace.mutate(name, {
      onSuccess: (ws) => {
        setActiveWorkspaceId(ws.id);
        setTopicId(null);
        setView({ kind: "topic", id: 0 });
      },
    });
  };

  const handleRenameWorkspace = (id: number, name: string) =>
    renameWorkspace.mutateAsync({ id, name });

  const handleDeleteWorkspace = (id: number) => {
    deleteWorkspace.mutate(id, {
      onSuccess: () => {
        const fallback = workspaces.find((w) => w.id !== id);
        setActiveWorkspaceId(fallback?.id ?? null);
        setTopicId(null);
        setView({ kind: "topic", id: 0 });
      },
    });
  };

  const handleRenameTopic = (id: number, title: string) =>
    renameTopic.mutateAsync({ topicId: id, title });

  const clearActiveTopic = (id: number) => {
    if (topicId === id || (view.kind === "topic" && view.id === id)) {
      setTopicId(null);
      setView({ kind: "topic", id: 0 });
    }
  };

  const handleArchiveTopic = (id: number) =>
    archiveTopic.mutateAsync(id, {
      onSuccess: () => clearActiveTopic(id),
    });

  const handleRestoreTopic = (id: number) =>
    restoreTopic.mutateAsync(id, {
      onSuccess: () => {
        setView({ kind: "topic", id });
        setTopicId(id);
      },
    });

  const handleDeleteTopic = (id: number) =>
    deleteTopic.mutateAsync(id, {
      onSuccess: () => clearActiveTopic(id),
    });

  const handleRemoveWorkspaceMember = (humanId: number) => {
    if (activeWorkspaceId === null) return Promise.resolve();
    return removeWorkspaceMember.mutateAsync(humanId);
  };

  const handleRemoveWorkspaceAgent = (agentId: number) => {
    if (activeWorkspaceId === null) return Promise.resolve();
    return removeWorkspaceAgent.mutateAsync(agentId);
  };

  const [activeInvite, setActiveInvite] = useState<WorkspaceInvite | null>(null);
  const [showInviteAgent, setShowInviteAgent] = useState(false);
  const createInvite = useCreateInvite();

  const handleInviteMember = () => {
    if (!activeWorkspace) return;
    createInvite.mutate(activeWorkspace.id, {
      onSuccess: (inv) => setActiveInvite(inv),
    });
  };

  const handleInviteAgent = () => {
    if (!activeWorkspace) return;
    setShowInviteAgent(true);
  };

  const handleSelectTopic = (id: number) => {
    setView({ kind: "topic", id });
    setTopicId(id);
    if (isMobile) setMobileTab("topic");
  };

  const sidebar = (
    <Sidebar
      activeWorkspace={activeWorkspace}
      workspaces={workspaces}
      topics={topics}
      allTopics={allTopics}
      archivedTopics={archivedTopics}
      members={members}
      activeTopicId={view.kind === "topic" ? view.id : null}
      onSelectTopic={handleSelectTopic}
      onCreateTopic={
        activeWorkspaceId === null
          ? () => {}
          : async (input) => {
              await createTopic.mutateAsync(input);
            }
      }
      onSwitchWorkspace={handleSwitchWorkspace}
      onCreateWorkspace={handleCreateWorkspace}
      onRenameWorkspace={handleRenameWorkspace}
      onDeleteWorkspace={handleDeleteWorkspace}
      onRenameTopic={handleRenameTopic}
      onArchiveTopic={handleArchiveTopic}
      onRestoreTopic={handleRestoreTopic}
      onDeleteTopic={handleDeleteTopic}
      onInviteMember={handleInviteMember}
      onInviteAgent={handleInviteAgent}
      canManageMembers={activeWorkspace?.my_role === "owner"}
      onRemoveMember={handleRemoveWorkspaceMember}
      onRemoveAgent={handleRemoveWorkspaceAgent}
      onClickSettings={() => {
        setView({ kind: "settings-tokens" });
        if (isMobile) setMobileTab("workspace");
      }}
      onSelectAgent={(id) => {
        setView({ kind: "agent-detail", id });
        if (isMobile) setMobileTab("workspace");
      }}
    />
  );

  const activeTopicId = view.kind === "topic" && view.id > 0 ? view.id : topicId;
  const userName = session.data?.human.name ?? "you";

  useEffect(() => {
    if (!isMobile) setMobileBoardOpen(false);
  }, [isMobile]);

  const topicMain = (id: number) => (
    <div className="flex flex-col h-full min-h-0">
      <div className="flex-1 min-h-0">
        <TopicView
          topicId={id}
          workspaceMembers={members}
          onOpenResources={isMobile ? () => setMobileBoardOpen(true) : undefined}
        />
      </div>
    </div>
  );

  let main: React.ReactNode;
  if (isMobile) {
    if (mobileTab === "workspace") {
      if (view.kind === "settings-tokens") main = <SettingsTokensPage />;
      else if (view.kind === "agents") main = <AgentList onSelectAgent={(id) => setView({ kind: "agent-detail", id })} />;
      else if (view.kind === "agent-detail") main = <AgentDetail agentId={view.id} onBack={() => setView({ kind: "agents" })} />;
      else main = <div className="h-full overflow-y-auto bg-surface">{sidebar}</div>;
    }
    else if (!activeTopicId)
      main = <div className="h-full overflow-y-auto bg-surface">{sidebar}</div>;
    else if (mobileTab === "topic" && activeTopicId)
      main = topicMain(activeTopicId);
    else main = <div className="p-6 text-text-dim">加载中…</div>;
  } else if (view.kind === "topic" && view.id > 0) {
    main = topicMain(view.id);
  } else if (view.kind === "attention") {
    main = <AttentionView userName={userName} />;
  } else if (view.kind === "settings-tokens") {
    main = <SettingsTokensPage />;
  } else if (view.kind === "agents") {
    main = <AgentList onSelectAgent={(id) => setView({ kind: "agent-detail", id })} />;
  } else if (view.kind === "agent-detail") {
    main = <AgentDetail agentId={view.id} onBack={() => setView({ kind: "topic", id: activeTopicId ?? 0 })} />;
  } else {
    main = <div className="p-6 text-text-dim">加载中…</div>;
  }

  const context =
    view.kind === "topic" && activeTopicId ? (
      <TopicContext topicId={activeTopicId} projectId={activeWorkspaceId} />
    ) : view.kind === "agents" || view.kind === "agent-detail" ? (
      <div className="p-4 text-text-dim text-sm">管理你拥有的 agent；workspace 成员关系在左侧成员区体现。</div>
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
    <>
      <AppShell
        sidebar={sidebar}
        sidebarRail={sidebarRail}
        main={main}
        context={context}
        bottomTabs={<BottomTabs active={mobileTab} onSelect={setMobileTab} />}
      />
      {activeInvite && (
        <InviteDialog
          workspaceName={activeWorkspace?.name ?? ""}
          joinUrl={activeInvite.join_url}
          onClose={() => setActiveInvite(null)}
        />
      )}
      {showInviteAgent && activeWorkspace && (
        <InviteAgentDialog
          workspaceName={activeWorkspace.name}
          workspaceSlug={activeWorkspace.slug}
          onClose={() => setShowInviteAgent(false)}
        />
      )}
      {isMobile && mobileBoardOpen && activeTopicId && (
        <div className="fixed inset-0 z-50 bg-[rgba(44,42,38,0.28)]" role="dialog" aria-modal="true" aria-label="AI 看板">
          <button
            type="button"
            aria-label="关闭 AI 看板"
            className="absolute inset-0 h-full w-full cursor-default"
            onClick={() => setMobileBoardOpen(false)}
          />
          <section className="absolute inset-x-0 bottom-0 flex max-h-[88dvh] min-h-[55dvh] flex-col rounded-t-lg border border-border-soft bg-surface shadow-[0_-18px_50px_rgba(44,42,38,0.20)]">
            <div className="flex items-center justify-between border-b border-border-soft px-4 py-3">
              <div>
                <div className="font-[var(--font-display)] text-[18px] font-semibold text-text">AI 看板</div>
                <div className="text-[12px] text-text-dim">当前话题的思路、建议和产物</div>
              </div>
              <button
                type="button"
                onClick={() => setMobileBoardOpen(false)}
                className="grid h-8 w-8 place-items-center rounded-[3px] text-[18px] leading-none text-text-dim hover:bg-surface-hover hover:text-text"
                aria-label="关闭 AI 看板"
              >
                ×
              </button>
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto px-3 py-3">
              <TopicContext topicId={activeTopicId} projectId={activeWorkspaceId} />
            </div>
          </section>
        </div>
      )}
    </>
  );
}

function useMediaQuery(query: string) {
  const [matches, setMatches] = useState(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
      return false;
    }
    return window.matchMedia(query).matches;
  });

  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
      return;
    }
    const mql = window.matchMedia(query);
    const update = () => setMatches(mql.matches);
    update();
    mql.addEventListener("change", update);
    return () => mql.removeEventListener("change", update);
  }, [query]);

  return matches;
}
