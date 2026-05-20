import { useState } from "react";
import { useAgentsOnline } from "../api/queries";
import type { TopicDTO } from "../api/types";
import { cn } from "../lib/cn";

interface SidebarProps {
  projectName: string;
  projectRepo: string;
  topics: TopicDTO[];
  activeTopicId: number | null;
  attentionCount?: number;
  onClickAttention?: () => void;
  onSelectTopic?: (id: number) => void;
  onClickSettings?: () => void;
}

export function Sidebar({
  projectName,
  projectRepo,
  topics,
  activeTopicId,
  attentionCount = 0,
  onClickAttention,
  onSelectTopic,
  onClickSettings,
}: SidebarProps) {
  const online = useAgentsOnline();
  const onlineList = online.data ?? [];

  return (
    <div className="flex flex-col h-full">
      <div className="px-5 pt-5 pb-4 border-b border-border-soft flex items-center gap-3">
        <div className="w-7 h-7 rounded-lg bg-text text-bg grid place-items-center font-bold text-sm font-[var(--font-display)]">
          {projectName[0] ?? "L"}
        </div>
        <div className="leading-tight min-w-0">
          <div className="font-[var(--font-display)] font-semibold text-[15px] truncate">
            {projectName}
          </div>
          <div className="text-text-dim text-[11px] font-mono mt-px truncate">
            {projectRepo}
          </div>
        </div>
      </div>

      <div className="p-3">
        <button
          className="w-full flex items-center justify-between px-3 py-2 rounded text-xs uppercase tracking-wider font-semibold text-text-dim hover:bg-surface-hover hover:text-text"
          type="button"
          onClick={onClickAttention}
        >
          <span>待处理</span>
          {attentionCount > 0 && (
            <span className="bg-accent-soft text-accent-text px-2 py-px rounded-full text-[10px] font-mono">
              {attentionCount}
            </span>
          )}
        </button>
      </div>

      <Section label="话题" count={topics.length}>
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
        label="在线 Agent"
        count={onlineList.length}
        hint="近 5 分钟用 token 调过 Lets 的 agent"
      >
        {onlineList.length === 0 ? (
          <div className="px-3 py-1 text-[11px] text-text-dim italic leading-relaxed">
            目前没有 agent 连上。<br />
            在本地终端跑 <span className="font-mono">claude</span> 或 <span className="font-mono">codex</span>，并把 Lets 的 token 写进 <span className="font-mono">.mcp.json</span> 后，它们会在这里出现。
          </div>
        ) : (
          onlineList.map((a) => (
            <ChannelRow
              key={a.agent_instance_id}
              tag={
                a.role === "claude"
                  ? "CC"
                  : a.role === "codex"
                    ? "CX"
                    : a.role.slice(0, 2).toUpperCase()
              }
              title={`${a.role} · ${a.device_label}`}
            />
          ))
        )}
      </Section>

      <div className="flex-1 min-h-3" />

      <div className="border-t border-border-soft px-4 py-3 flex flex-col gap-0.5">
        <FooterLink>项目设置</FooterLink>
        <FooterLink onClick={onClickSettings}>个人设置</FooterLink>
      </div>
    </div>
  );
}

function Section({
  label,
  count,
  hint,
  children,
  defaultOpen = true,
}: {
  label: string;
  count: number;
  hint?: string;
  children?: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="p-3 pt-1">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        title={hint}
        className="w-full flex items-center gap-2 px-3 py-1.5 rounded text-[11px] font-semibold text-text-dim hover:bg-surface-hover hover:text-text"
      >
        <span
          className="text-[9px] text-text-dim transition-transform"
          style={{ transform: open ? "rotate(90deg)" : "rotate(0deg)" }}
        >
          ▶
        </span>
        <span className="flex-1 text-left">{label}</span>
        <span className="font-mono font-medium">{count}</span>
      </button>
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
        "w-full flex items-center gap-2 px-3 py-1 rounded text-[12px] text-left",
        active
          ? "bg-surface-hover text-text"
          : "text-text-muted hover:bg-surface-hover hover:text-text",
      )}
    >
      <span className="font-mono text-[11px] text-text-dim w-12 flex-shrink-0">{tag}</span>
      <span className="truncate">{title}</span>
    </button>
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
