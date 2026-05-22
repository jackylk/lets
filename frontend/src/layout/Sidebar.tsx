import { useEffect, useRef, useState, type ReactNode } from "react";
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
  onRenameWorkspace?: (id: number, name: string) => void | Promise<unknown>;
  onDeleteWorkspace?: (id: number) => void;
  onRenameTopic?: (id: number, title: string) => void | Promise<unknown>;
  onInviteMember: () => void;
  onInviteAgent?: () => void;
  onClickSettings?: () => void;
  onClickAgents?: () => void;
  onSelectAgent?: (agentId: number) => void;
}

interface TopicRowProps {
  topic: TopicDTO;
  active: boolean;
  onSelect: () => void;
  onRename?: (id: number, title: string) => void | Promise<unknown>;
}

function TopicRow({ topic, active, onSelect, onRename }: TopicRowProps) {
  const rowRef = useRef<HTMLDivElement>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [renaming, setRenaming] = useState(false);
  const [title, setTitle] = useState(topic.title);

  useEffect(() => {
    if (!menuOpen) return;
    function onPointerDown(event: MouseEvent) {
      if (!rowRef.current?.contains(event.target as Node)) setMenuOpen(false);
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setMenuOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [menuOpen]);

  async function submitRename() {
    const next = title.trim();
    if (!next || next === topic.title) {
      setRenaming(false);
      setTitle(topic.title);
      return;
    }
    await onRename?.(topic.id, next);
    setRenaming(false);
    setMenuOpen(false);
  }

  return (
    <div
      ref={rowRef}
      className={cn(
        "group relative flex w-full items-center rounded text-[12.5px]",
        active
          ? "bg-surface-elev text-text shadow-[inset_0_0_0_1px_var(--color-border)]"
          : "text-text-muted hover:text-text hover:shadow-[inset_2px_0_0_var(--color-accent)]",
      )}
    >
      {renaming ? (
        <div className="flex min-w-0 flex-1 items-center gap-2 px-3 py-1">
          <span className="w-12 flex-shrink-0 font-mono text-[11px] text-text-dim">
            {topic.slug.slice(0, 6).toUpperCase()}
          </span>
          <input
            autoFocus
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") void submitRename();
              if (e.key === "Escape") {
                setRenaming(false);
                setTitle(topic.title);
              }
            }}
            className="min-w-0 flex-1 rounded border border-border bg-bg px-1.5 py-0.5 text-[12.5px] text-text outline-none focus:border-accent-border"
          />
        </div>
      ) : (
        <button
          type="button"
          onClick={onSelect}
          className="flex min-w-0 flex-1 items-center gap-2 px-3 py-2 md:py-1 text-left"
        >
          <span className="w-12 flex-shrink-0 font-mono text-[11px] text-text-dim">
            {topic.slug.slice(0, 6).toUpperCase()}
          </span>
          <span className="truncate">{topic.title}</span>
        </button>
      )}
      <button
        type="button"
        aria-label={`${topic.title} 话题操作`}
        title="话题操作"
        onClick={(e) => {
          e.stopPropagation();
          setMenuOpen((v) => !v);
        }}
        className={cn(
          "mr-1 grid h-6 w-6 flex-shrink-0 place-items-center rounded text-text-dim hover:bg-surface-hover hover:text-text",
          active || menuOpen ? "opacity-100" : "opacity-0 group-hover:opacity-100",
        )}
      >
        ⋯
      </button>
      {menuOpen && (
        <div className="absolute right-1 top-7 z-20 w-44 rounded-md border border-border bg-surface-elev p-1 shadow-[0_12px_32px_rgba(44,42,38,0.14)]">
          <TopicMenuItem
            onClick={() => {
              setRenaming(true);
              setMenuOpen(false);
            }}
          >
            重命名
          </TopicMenuItem>
          <TopicMenuItem
            onClick={() => {
              void navigator.clipboard?.writeText(window.location.href);
              setMenuOpen(false);
            }}
          >
            复制链接
          </TopicMenuItem>
          <TopicMenuItem disabled>静音</TopicMenuItem>
          <div className="my-1 border-t border-border-soft" />
          <TopicMenuItem disabled>归档</TopicMenuItem>
          <TopicMenuItem danger disabled>删除</TopicMenuItem>
        </div>
      )}
    </div>
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
  onRenameWorkspace,
  onDeleteWorkspace,
  onRenameTopic,
  onInviteMember,
  onInviteAgent,
  onClickSettings,
  onClickAgents,
  onSelectAgent,
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
        onRename={onRenameWorkspace}
        onDelete={onDeleteWorkspace}
        onInviteMember={onInviteMember}
        onInviteAgent={onInviteAgent}
        onSettings={onClickSettings}
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
            className="w-7 h-7 md:w-5 md:h-5 grid place-items-center rounded-[3px] text-text-dim hover:bg-surface-hover hover:text-text text-[16px] md:text-[14px] leading-none"
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
                onRename={onRenameTopic}
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
        workspaceName={activeWorkspace?.name}
        members={members}
        onInvite={onInviteMember}
        onInviteAgent={onInviteAgent}
        onSelectAgent={onSelectAgent}
      />

      {/* Footer */}
      {(onClickAgents || onClickSettings) && (
        <div className="border-t border-border-soft px-4 py-3 flex flex-col gap-0.5">
          {onClickAgents && <FooterLink onClick={onClickAgents}>Agents</FooterLink>}
          {onClickSettings && <FooterLink onClick={onClickSettings}>设置</FooterLink>}
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

function TopicMenuItem({
  children,
  onClick,
  danger,
  disabled,
}: {
  children: ReactNode;
  onClick?: () => void;
  danger?: boolean;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className={cn(
        "flex w-full items-center rounded px-2.5 py-1.5 text-left text-[12.5px]",
        danger
          ? "text-accent-text hover:bg-accent-soft"
          : "text-text-muted hover:bg-surface-hover hover:text-text",
        disabled && "cursor-not-allowed opacity-45 hover:bg-transparent",
      )}
    >
      {children}
    </button>
  );
}
