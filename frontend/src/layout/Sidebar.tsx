import { useState } from "react";
import { WorkspaceSwitcher } from "../workspace/WorkspaceSwitcher";
import { WorkspaceSection } from "../workspace/WorkspaceSection";
import { CreateWorkspaceInline } from "../workspace/CreateWorkspaceInline";
import { MembersList } from "../workspace/MembersList";
import { cn } from "../lib/cn";
import type { TopicDTO, Workspace, WorkspaceMember } from "../api/types";

interface Props {
  activeWorkspace: Workspace | undefined;
  workspaces: Workspace[];
  topics: TopicDTO[];
  members: WorkspaceMember[];
  activeTopicId: number | null;
  onSelectTopic: (id: number) => void;
  onCreateTopic: (t: { slug: string; title: string }) => void;
  onSwitchWorkspace: (id: number) => void;
  onCreateWorkspace: (name: string) => void;
  onInviteMember: () => void;
  onInviteAgent?: () => void;
  onClickSettings?: () => void;
}

interface TopicRowProps {
  topic: TopicDTO;
  active: boolean;
  onSelect: () => void;
}

function TopicRow({ topic, active, onSelect }: TopicRowProps) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        "w-full flex items-center gap-2 px-3 py-1 rounded text-[12.5px] text-left",
        active
          ? "bg-surface-elev text-text shadow-[inset_0_0_0_1px_var(--color-border)]"
          : "text-text-muted hover:text-text hover:shadow-[inset_2px_0_0_var(--color-accent)]",
      )}
    >
      <span className="font-mono text-[11px] text-text-dim w-12 flex-shrink-0">
        {topic.slug.slice(0, 6).toUpperCase()}
      </span>
      <span className="truncate">{topic.title}</span>
    </button>
  );
}

export function Sidebar({
  activeWorkspace,
  workspaces,
  topics,
  members,
  activeTopicId,
  onSelectTopic,
  onCreateTopic,
  onSwitchWorkspace,
  onCreateWorkspace,
  onInviteMember,
  onInviteAgent,
  onClickSettings,
}: Props) {
  const [creating, setCreating] = useState(false);

  const otherWorkspaces = workspaces.filter(
    (w) => w.id !== activeWorkspace?.id,
  );

  return (
    <div className="flex flex-col h-full">
      {/* Workspace switcher header */}
      <WorkspaceSwitcher
        workspaces={workspaces}
        activeId={activeWorkspace?.id ?? -1}
        onSelect={onSwitchWorkspace}
        onCreate={() => setCreating(true)}
      />

      {/* Inline create-workspace form */}
      {creating && (
        <CreateWorkspaceInline
          onSubmit={(name) => {
            onCreateWorkspace(name);
            setCreating(false);
          }}
          onCancel={() => setCreating(false)}
        />
      )}

      {/* Active workspace topics */}
      <div className="p-3 pt-1 border-b border-border-soft">
        <div className="w-full flex items-center gap-2 px-3 py-1.5 rounded text-[11px] font-semibold text-text-dim">
          <span className="flex-1">话题</span>
          <span className="font-mono font-medium">{topics.length}</span>
          <button
            type="button"
            aria-label="新建话题"
            title="新建话题"
            onClick={() =>
              onCreateTopic({
                slug: `topic-${Date.now().toString(36)}`,
                title: "新话题",
              })
            }
            className="w-5 h-5 grid place-items-center rounded-[3px] text-text-dim hover:bg-surface-hover hover:text-text text-[14px] leading-none"
          >
            +
          </button>
        </div>
        <div className="mt-1 flex flex-col gap-0.5">
          {topics.length === 0 ? (
            <div className="px-3 py-1 text-[11px] text-text-dim italic">
              还没有话题
            </div>
          ) : (
            topics.map((t) => (
              <TopicRow
                key={t.id}
                topic={t}
                active={activeTopicId === t.id}
                onSelect={() => onSelectTopic(t.id)}
              />
            ))
          )}
        </div>
      </div>

      {/* Other workspaces — collapsed sections */}
      {otherWorkspaces.length > 0 && (
        <div className="border-b border-border-soft py-1">
          {otherWorkspaces.map((w) => (
            <WorkspaceSection
              key={w.id}
              workspace={w}
              onSelectTopic={(wsId, topicId) => {
                onSwitchWorkspace(wsId);
                onSelectTopic(topicId);
              }}
            />
          ))}
        </div>
      )}

      <div className="flex-1 min-h-3" />

      {/* Members list */}
      <MembersList
        members={members}
        onInvite={onInviteMember}
        onInviteAgent={onInviteAgent}
      />

      {/* Footer */}
      {onClickSettings && (
        <div className="border-t border-border-soft px-4 py-3 flex flex-col gap-0.5">
          <FooterLink onClick={onClickSettings}>设置</FooterLink>
        </div>
      )}
    </div>
  );
}

function FooterLink({ children, onClick }: { children: string; onClick?: () => void }) {
  return (
    <div
      role={onClick ? "button" : undefined}
      onClick={onClick}
      className="px-2 py-1.5 rounded text-xs text-text-muted hover:bg-surface-hover hover:text-text cursor-pointer"
    >
      {children}
    </div>
  );
}
