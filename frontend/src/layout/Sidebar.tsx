import { useState, type FormEvent } from "react";
import { useAllAgents } from "../api/queries";
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
  onCreateTopic?: (input: { slug: string; title: string }) => void | Promise<void>;
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
  onCreateTopic,
}: SidebarProps) {
  const agents = useAllAgents();
  const agentList = agents.data ?? [];
  const onlineCount = agentList.filter((a) => a.is_online).length;
  const [composing, setComposing] = useState(false);

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
          className="w-full flex items-center justify-between px-3 py-2 rounded text-xs font-semibold text-text-dim hover:bg-surface-hover hover:text-text"
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
              setComposing(true);
            }}
            className="w-5 h-5 grid place-items-center rounded text-text-dim hover:bg-surface-hover hover:text-text text-[14px] leading-none"
          >
            +
          </button>
        }
      >
        {composing && onCreateTopic && (
          <NewTopicRow
            onCancel={() => setComposing(false)}
            onSubmit={async (input) => {
              await onCreateTopic(input);
              setComposing(false);
            }}
          />
        )}
        {topics.length === 0 && !composing ? (
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
            还没有 agent。运行 <span className="font-mono">scripts/connect_local_agents.sh</span> 给你的本地 CC / Codex 发 token。
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
        <FooterLink>项目设置</FooterLink>
        <FooterLink onClick={onClickSettings}>个人设置</FooterLink>
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
            ▶
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

function NewTopicRow({
  onCancel,
  onSubmit,
}: {
  onCancel: () => void;
  onSubmit: (input: { slug: string; title: string }) => Promise<void> | void;
}) {
  const [title, setTitle] = useState("");
  const [slug, setSlug] = useState("");
  const [busy, setBusy] = useState(false);

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    const finalSlug =
      slug.trim() ||
      title
        .trim()
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-+|-+$/g, "")
        .slice(0, 24) ||
      `topic-${Date.now()}`;
    setBusy(true);
    Promise.resolve(onSubmit({ slug: finalSlug, title: title.trim() })).finally(() =>
      setBusy(false),
    );
  }

  return (
    <form
      onSubmit={submit}
      className="mx-3 px-2 py-2 mb-1 rounded border border-border bg-surface-elev flex flex-col gap-1.5"
    >
      <input
        autoFocus
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="话题标题"
        className="text-[12px] bg-transparent outline-none"
      />
      <input
        value={slug}
        onChange={(e) => setSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-]+/g, "-"))}
        placeholder="slug (留空自动生成)"
        className="text-[11px] font-mono bg-transparent outline-none text-text-muted"
      />
      <div className="flex justify-end gap-2 mt-0.5">
        <button
          type="button"
          onClick={onCancel}
          className="text-[11px] text-text-dim hover:text-text px-2 py-0.5"
        >
          取消
        </button>
        <button
          type="submit"
          disabled={!title.trim() || busy}
          className="text-[11px] bg-text text-bg px-2 py-0.5 rounded disabled:opacity-40"
        >
          {busy ? "…" : "创建"}
        </button>
      </div>
    </form>
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
