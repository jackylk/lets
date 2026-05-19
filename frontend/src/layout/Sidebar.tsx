import { useState } from "react";

interface SidebarProps {
  projectName: string;
  projectRepo: string;
  attentionCount?: number;
  onClickAttention?: () => void;
  onClickTopic?: () => void;
  onClickSettings?: () => void;
}

export function Sidebar({
  projectName,
  projectRepo,
  attentionCount = 0,
  onClickAttention,
  onClickTopic,
  onClickSettings,
}: SidebarProps) {
  return (
    <div className="flex flex-col h-full">
      <div className="px-5 pt-5 pb-4 border-b border-border-soft flex items-center gap-3">
        <div className="w-7 h-7 rounded-lg bg-text text-bg grid place-items-center font-bold text-sm font-[var(--font-display)]">
          {projectName[0]}
        </div>
        <div className="leading-tight">
          <div className="font-[var(--font-display)] font-semibold text-[15px]">{projectName}</div>
          <div className="text-text-dim text-[11px] font-mono mt-px">{projectRepo}</div>
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

      <Section label="Channels" count={1}>
        <ChannelRow
          tag="T-PPT"
          title="为 Agent 记忆写一个研讨 PPT"
          onClick={onClickTopic}
        />
      </Section>
      <Section label="Online" count={3}>
        <ChannelRow tag="CC" title="claude · neo-mbp" />
        <ChannelRow tag="CC" title="claude · trinity-air" />
        <ChannelRow tag="CX" title="codex · neo-mbp" />
      </Section>
      <Section label="Direct Messages" count={1}>
        <ChannelRow tag="M" title="Morpheus" />
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
  children,
  defaultOpen = true,
}: {
  label: string;
  count: number;
  children?: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="p-3 pt-1">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-2 px-3 py-1.5 rounded text-[11px] uppercase tracking-wider font-semibold text-text-dim hover:bg-surface-hover hover:text-text"
      >
        <span
          className="text-[9px] text-text-dim transition-transform"
          style={{ transform: open ? "rotate(90deg)" : "rotate(0deg)" }}
        >
          ▶
        </span>
        <span className="flex-1 text-left">{label}</span>
        <span className="font-mono normal-case font-medium tracking-normal">{count}</span>
      </button>
      {open && children && <div className="mt-1 flex flex-col gap-0.5">{children}</div>}
    </div>
  );
}

function ChannelRow({
  tag,
  title,
  onClick,
}: {
  tag: string;
  title: string;
  onClick?: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="w-full flex items-center gap-2 px-3 py-1 rounded text-[12px] text-text-muted hover:bg-surface-hover hover:text-text text-left"
    >
      <span className="font-mono text-[11px] text-text-dim w-8 flex-shrink-0">{tag}</span>
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
