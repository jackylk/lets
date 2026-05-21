import { useState } from "react";
import { useAllAgents } from "../api/queries";
import type { TopicDTO } from "../api/types";
import { cn } from "../lib/cn";

interface SidebarProps {
  topics: TopicDTO[];
  activeTopicId: number | null;
  attentionCount?: number;
  onClickAttention?: () => void;
  onSelectTopic?: (id: number) => void;
  onClickSettings?: () => void;
  onCreateTopic?: (input: { slug: string; title: string }) => void | Promise<void>;
}

export function Sidebar({
  topics,
  activeTopicId,
  attentionCount = 0,
  onClickAttention,
  onSelectTopic,
  onClickSettings,
  onCreateTopic,
}: SidebarProps) {
  const agents = useAllAgents();
  const agentList = agents.data ?? [];
  const onlineCount = agentList.filter((a) => a.is_online).length;

  return (
    <div className="flex flex-col h-full">
      <div className="px-5 pt-5 pb-5 border-b border-border-soft">
        <div className="font-[var(--font-display)] font-semibold text-[34px] leading-none tracking-tight text-text">
          Lets
        </div>
        <div className="text-text-dim text-[11.5px] italic mt-2 leading-snug">
          a board for humans + agents
        </div>
      </div>

      <div className="p-3">
        <button
          className="w-full flex items-center justify-between px-3 py-2 rounded text-xs font-semibold text-text-dim hover:text-text hover:shadow-[inset_2px_0_0_var(--color-accent)]"
          type="button"
          onClick={onClickAttention}
        >
          <span>待处理</span>
          {attentionCount > 0 && (
            <span className="bg-accent-soft text-accent-text border border-accent-border px-2 py-px rounded-[3px] text-[10px] font-mono">
              {attentionCount}
            </span>
          )}
        </button>
      </div>

      <Section
        label="话题"
        count={topics.length}
        action={
          <button
            type="button"
            aria-label="新建话题"
            title="新建话题"
            onClick={(e) => {
              e.stopPropagation();
              void onCreateTopic?.({
                slug: `topic-${Date.now().toString(36)}`,
                title: "新对话",
              });
            }}
            className="w-5 h-5 grid place-items-center rounded-[3px] text-text-dim hover:bg-surface-hover hover:text-text text-[14px] leading-none"
          >
            +
          </button>
        }
      >
        {topics.length === 0 ? (
          <div className="px-3 py-1 text-[11px] text-text-dim italic">
            还没有话题
          </div>
        ) : (
          topics.map((t) => (
            <ChannelRow
              key={t.id}
              tag={t.slug.slice(0, 6).toUpperCase()}
              title={t.title}
              active={activeTopicId === t.id}
              onClick={() => onSelectTopic?.(t.id)}
            />
          ))
        )}
      </Section>

      <Section
        label="Agent"
        count={agentList.length}
        rightCount={`${onlineCount} 在线`}
        hint="所有 agent_instance。绿点=近 5 分钟有 token 调用过 Lets；灰点=离线"
      >
        {agentList.length === 0 ? (
          <div className="px-3 py-1 text-[11px] text-text-dim italic leading-relaxed">
            还没有 agent。在主区按提示运行那条 <span className="font-mono">curl … /install</span> 命令把这台电脑接上来。
          </div>
        ) : (
          agentList.map((a) => (
            <AgentRow
              key={a.agent_instance_id}
              role={a.role}
              deviceLabel={a.device_label}
              humanName={a.human_name}
              isOnline={!!a.is_online}
              lastSeenAt={a.last_seen_at}
            />
          ))
        )}
      </Section>

      <div className="flex-1 min-h-3" />

      <div className="border-t border-border-soft px-4 py-3 flex flex-col gap-0.5">
        <FooterLink onClick={onClickSettings}>设置</FooterLink>
      </div>
    </div>
  );
}

function Section({
  label,
  count,
  rightCount,
  hint,
  action,
  children,
  defaultOpen = true,
}: {
  label: string;
  count: number;
  rightCount?: string;
  hint?: string;
  action?: React.ReactNode;
  children?: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="p-3 pt-1">
      <div className="w-full flex items-center gap-2 px-3 py-1.5 rounded text-[11px] font-semibold text-text-dim">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          title={hint}
          className="flex items-center gap-2 flex-1 text-left hover:text-text"
        >
          <span
            className="text-[9px] text-text-dim transition-transform"
            style={{ transform: open ? "rotate(90deg)" : "rotate(0deg)" }}
          >
            ›
          </span>
          <span>{label}</span>
          <span className="font-mono font-medium">{count}</span>
          {rightCount && (
            <span className="font-mono font-normal text-[10px] text-text-dim ml-1">
              · {rightCount}
            </span>
          )}
        </button>
        {action}
      </div>
      {open && children && <div className="mt-1 flex flex-col gap-0.5">{children}</div>}
    </div>
  );
}

function ChannelRow({
  tag,
  title,
  active,
  onClick,
}: {
  tag: string;
  title: string;
  active?: boolean;
  onClick?: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "w-full flex items-center gap-2 px-3 py-1 rounded text-[12.5px] text-left",
        active
          ? "bg-surface-elev text-text shadow-[inset_0_0_0_1px_var(--color-border)]"
          : "text-text-muted hover:text-text hover:shadow-[inset_2px_0_0_var(--color-accent)]",
      )}
    >
      <span className="font-mono text-[11px] text-text-dim w-12 flex-shrink-0">{tag}</span>
      <span className="truncate">{title}</span>
    </button>
  );
}

function AgentRow({
  role,
  deviceLabel,
  humanName,
  isOnline,
  lastSeenAt,
}: {
  role: string;
  deviceLabel: string;
  humanName: string;
  isOnline: boolean;
  lastSeenAt: string | null;
}) {
  const tag = role === "claude" ? "CC" : role === "codex" ? "CX" : role.slice(0, 2).toUpperCase();
  return (
    <div
      className="w-full flex items-center gap-2 px-3 py-1 rounded text-[12px] text-text-muted"
      title={
        isOnline
          ? `${humanName} · ${role} · ${deviceLabel} · 在线`
          : lastSeenAt
            ? `${humanName} · ${role} · ${deviceLabel} · 上次活跃 ${lastSeenAt}`
            : `${humanName} · ${role} · ${deviceLabel} · 从未连过`
      }
    >
      <span
        aria-label={isOnline ? "在线" : "离线"}
        className={cn(
          "inline-block w-2 h-2 rounded-full shrink-0",
          isOnline ? "bg-status-on" : "bg-text-dim/40",
        )}
      />
      <span className="font-mono text-[11px] text-text-dim w-12 flex-shrink-0">{tag}</span>
      <span className={cn("truncate", !isOnline && "opacity-60")}>
        {role} · {deviceLabel}
      </span>
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
