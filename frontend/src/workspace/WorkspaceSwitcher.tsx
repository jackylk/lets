import { useEffect, useRef, useState, type ReactNode } from "react";
import type { Workspace } from "../api/types";
import { cn } from "../lib/cn";

interface Props {
  workspaces: Workspace[];
  activeId: number;
  onSelect: (id: number) => void;
  onCreate: () => void;
  onRename?: (id: number, name: string) => void | Promise<unknown>;
  onInviteMember?: () => void;
  onInviteAgent?: () => void;
  onSettings?: () => void;
  onDelete?: (id: number) => void;
}

export function WorkspaceSwitcher({
  workspaces,
  activeId,
  onSelect,
  onCreate,
  onRename,
  onInviteMember,
  onInviteAgent,
  onSettings,
  onDelete,
}: Props) {
  const active = workspaces.find((w) => w.id === activeId);
  const others = workspaces.filter((w) => w.id !== activeId).slice(0, 2);
  const menuRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [renaming, setRenaming] = useState(false);
  const [draftName, setDraftName] = useState("");

  useEffect(() => {
    if (!open) return;
    function onPointerDown(event: MouseEvent) {
      if (!menuRef.current?.contains(event.target as Node)) setOpen(false);
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  function startRename() {
    if (!active) return;
    setDraftName(active.name);
    setRenaming(true);
  }

  async function submitRename() {
    if (!active || !onRename) return;
    const name = draftName.trim();
    if (!name || name === active.name) {
      setRenaming(false);
      return;
    }
    await onRename(active.id, name);
    setRenaming(false);
    setOpen(false);
  }

  function deleteActive() {
    if (!active || !onDelete) return;
    const confirmed = window.confirm(`删除工作区「${active.name}」？这个操作会隐藏它和其中的话题。`);
    if (!confirmed) return;
    onDelete(active.id);
    setOpen(false);
  }

  return (
    <div className="relative flex items-center gap-1 px-3 py-2 pr-11 border-b border-border">
      <div ref={menuRef} className="relative min-w-0">
        <button
          type="button"
          aria-expanded={open}
          onClick={() => setOpen((v) => !v)}
          className="flex max-w-[168px] items-center gap-1 rounded px-2 py-1 font-[var(--font-display)] text-sm text-text hover:bg-surface-hover"
        >
          <span className="truncate">{active?.name ?? "—"}</span>
          <span className="text-text-dim">▾</span>
        </button>
        {open && active && (
          <div className="absolute left-0 top-9 z-30 w-64 rounded-md border border-border bg-surface-elev p-1 shadow-[0_14px_40px_rgba(44,42,38,0.16)]">
            <div className="px-2.5 py-2">
              <div className="truncate font-[var(--font-display)] text-sm text-text">
                {active.name}
              </div>
              <div className="text-[11px] text-text-dim">
                {active.my_role === "owner" ? "Owner" : "Member"}
              </div>
            </div>
            <MenuDivider />
            <MenuItem onClick={() => { onCreate(); setOpen(false); }}>新建工作区</MenuItem>
            {workspaces.length > 1 && (
              <div className="max-h-32 overflow-y-auto py-1">
                {workspaces.filter((w) => w.id !== activeId).map((w) => (
                  <MenuItem key={w.id} onClick={() => { onSelect(w.id); setOpen(false); }}>
                    切换到 {w.name}
                  </MenuItem>
                ))}
              </div>
            )}
            <MenuDivider />
            {renaming ? (
              <div className="px-2 py-1.5">
                <input
                  autoFocus
                  value={draftName}
                  onChange={(e) => setDraftName(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") void submitRename();
                    if (e.key === "Escape") setRenaming(false);
                  }}
                  className="w-full rounded border border-border bg-bg px-2 py-1 text-sm text-text outline-none focus:border-accent-border"
                />
                <div className="mt-1 flex justify-end gap-1">
                  <button
                    type="button"
                    onClick={() => setRenaming(false)}
                    className="rounded px-2 py-1 text-[11px] text-text-dim hover:bg-surface-hover hover:text-text"
                  >
                    取消
                  </button>
                  <button
                    type="button"
                    onClick={() => void submitRename()}
                    className="rounded bg-accent-soft px-2 py-1 text-[11px] font-semibold text-accent-text hover:bg-surface-hover"
                  >
                    保存
                  </button>
                </div>
              </div>
            ) : (
              <MenuItem onClick={startRename} disabled={!onRename || active.my_role !== "owner"}>
                重命名
              </MenuItem>
            )}
            <MenuItem onClick={() => { onInviteMember?.(); setOpen(false); }}>邀请成员</MenuItem>
            <MenuItem onClick={() => { onInviteAgent?.(); setOpen(false); }}>邀请 agent</MenuItem>
            <MenuItem onClick={() => { onSettings?.(); setOpen(false); }}>工作区设置</MenuItem>
            <MenuDivider />
            <MenuItem onClick={deleteActive} danger disabled={!onDelete || active.my_role !== "owner"}>
              删除工作区
            </MenuItem>
          </div>
        )}
      </div>
      {others.map((w) => (
        <button
          key={w.id}
          type="button"
          onClick={() => onSelect(w.id)}
          className="text-xs text-text-dim hover:text-text px-2 py-1 rounded hover:bg-surface-hover"
        >
          {w.name}
        </button>
      ))}
    </div>
  );
}

function MenuItem({
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

function MenuDivider() {
  return <div className="my-1 border-t border-border-soft" />;
}
