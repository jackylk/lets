import { useEffect, useRef, useState, type ReactNode } from "react";

interface AppShellProps {
  sidebar: ReactNode;
  /** Slim rail shown when the sidebar is collapsed (a couple of icons / vertical label). */
  sidebarRail?: ReactNode;
  main: ReactNode;
  context: ReactNode;
  bottomTabs?: ReactNode;
}

const COLLAPSED_KEY = "lets:sidebar-collapsed";
const CONTEXT_W_KEY = "lets:context-w";
const CONTEXT_OPEN_KEY = "lets:context-open";
const SIDEBAR_W_EXPANDED = 296;
const SIDEBAR_W_COLLAPSED = 48;
const CONTEXT_W_DEFAULT = 360;
const CONTEXT_W_MIN = 260;
const CONTEXT_W_MAX = 640;

function loadCollapsed(): boolean {
  try { return window.localStorage.getItem(COLLAPSED_KEY) === "1"; } catch { return false; }
}
function loadContextW(): number {
  try {
    const raw = window.localStorage.getItem(CONTEXT_W_KEY);
    if (!raw) return CONTEXT_W_DEFAULT;
    const n = parseInt(raw, 10);
    if (Number.isFinite(n)) return Math.max(CONTEXT_W_MIN, Math.min(CONTEXT_W_MAX, n));
  } catch { /* ignore */ }
  return CONTEXT_W_DEFAULT;
}
function loadContextOpen(): boolean {
  try { return window.localStorage.getItem(CONTEXT_OPEN_KEY) === "1"; } catch { return false; }
}

export function AppShell({ sidebar, sidebarRail, main, context, bottomTabs }: AppShellProps) {
  const [collapsed, setCollapsed] = useState<boolean>(loadCollapsed);
  const [contextW, setContextW] = useState<number>(loadContextW);
  const [contextOpen, setContextOpen] = useState<boolean>(loadContextOpen);

  useEffect(() => {
    try { window.localStorage.setItem(COLLAPSED_KEY, collapsed ? "1" : "0"); } catch { /* ignore */ }
  }, [collapsed]);
  useEffect(() => {
    try { window.localStorage.setItem(CONTEXT_W_KEY, String(contextW)); } catch { /* ignore */ }
  }, [contextW]);
  useEffect(() => {
    try { window.localStorage.setItem(CONTEXT_OPEN_KEY, contextOpen ? "1" : "0"); } catch { /* ignore */ }
  }, [contextOpen]);

  // Drag-to-resize the context drawer.
  const dragStart = useRef<{ x: number; startW: number } | null>(null);
  function onResizerDown(e: React.MouseEvent) {
    dragStart.current = { x: e.clientX, startW: contextW };
    document.body.classList.add("select-none", "cursor-col-resize");
    const onMove = (ev: MouseEvent) => {
      if (!dragStart.current) return;
      const dx = dragStart.current.x - ev.clientX;       // drag left ⇒ wider drawer
      const next = Math.max(
        CONTEXT_W_MIN,
        Math.min(CONTEXT_W_MAX, dragStart.current.startW + dx),
      );
      setContextW(next);
    };
    const onUp = () => {
      dragStart.current = null;
      document.body.classList.remove("select-none", "cursor-col-resize");
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  }
  function resetContextW() {
    setContextW(CONTEXT_W_DEFAULT);
  }

  const sideW = collapsed ? SIDEBAR_W_COLLAPSED : SIDEBAR_W_EXPANDED;

  return (
    <div
      data-testid="app-shell"
      className="grid h-[100dvh] relative"
      style={{
        gridTemplateColumns: `${sideW}px 1fr`,
        transition: "grid-template-columns .18s ease",
      }}
    >
      <aside
        data-testid="app-sidebar"
        data-collapsed={collapsed || undefined}
        className="relative border-r border-border-soft bg-surface overflow-hidden"
      >
        <button
          type="button"
          aria-label={collapsed ? "展开侧栏" : "收起侧栏"}
          title={collapsed ? "展开侧栏" : "收起侧栏"}
          onClick={() => setCollapsed((v) => !v)}
          className="absolute top-2 right-2 z-10 w-6 h-6 grid place-items-center rounded text-text-dim hover:text-text bg-bg/80 border border-border-soft text-[13px]"
        >
          {collapsed ? "›" : "‹"}
        </button>
        {collapsed ? (
          <div className="h-full overflow-hidden">{sidebarRail}</div>
        ) : (
          <div className="h-full overflow-y-auto">{sidebar}</div>
        )}
      </aside>

      <main className="flex flex-col min-w-0 overflow-hidden pb-14 md:pb-0">{main}</main>

      {/* Toggle button — fixed at top-right; hidden on narrow screens (where mobile uses a tab) */}
      {!contextOpen && (
        <button
          type="button"
          data-testid="app-context-toggle"
          aria-label="展开 context"
          title="展开 context"
          onClick={() => setContextOpen(true)}
          className="hidden xl:flex fixed top-3 right-3 z-30 items-center gap-1 px-2 py-1 rounded text-[11px] text-text-dim hover:text-text bg-bg/90 border border-border-soft shadow-sm"
        >
          context ‹
        </button>
      )}

      {/* Floating context drawer */}
      <aside
        data-testid="app-context"
        aria-hidden={!contextOpen}
        className={
          "hidden xl:flex flex-col fixed top-0 right-0 h-[100dvh] z-20 " +
          "border-l border-border-soft bg-surface shadow-xl " +
          "transition-transform duration-200 ease-out"
        }
        style={{
          width: `${contextW}px`,
          transform: contextOpen ? "translateX(0)" : "translateX(100%)",
        }}
      >
        {/* Resizer hairline on the drawer's left edge */}
        <div
          role="separator"
          aria-orientation="vertical"
          aria-label="拖动调整宽度"
          title="拖动调整宽度 · 双击重置"
          onMouseDown={onResizerDown}
          onDoubleClick={resetContextW}
          className="absolute left-0 top-0 bottom-0 w-[6px] -translate-x-1/2 cursor-col-resize group z-10"
        >
          <span className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[2px] h-10 bg-border group-hover:bg-accent-border rounded-full transition-colors" />
        </div>

        <div className="flex items-center justify-between px-3 py-2 border-b border-border-soft">
          <span className="text-[11px] uppercase tracking-wider font-semibold text-text-dim">
            context
          </span>
          <button
            type="button"
            aria-label="收起 context"
            title="收起 context"
            onClick={() => setContextOpen(false)}
            className="w-6 h-6 grid place-items-center rounded text-text-dim hover:text-text hover:bg-surface-hover text-[13px]"
          >
            ›
          </button>
        </div>

        <div className="flex-1 overflow-y-auto">{context}</div>
      </aside>

      {bottomTabs}
    </div>
  );
}
