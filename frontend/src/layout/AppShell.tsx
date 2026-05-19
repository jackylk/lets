import type { ReactNode } from "react";

interface AppShellProps {
  sidebar: ReactNode;
  main: ReactNode;
  context: ReactNode;
}

export function AppShell({ sidebar, main, context }: AppShellProps) {
  return (
    <div
      data-testid="app-shell"
      className="grid h-[100dvh]"
      style={{
        gridTemplateColumns: "var(--side-w, 296px) 1fr var(--context-w, 360px)",
      }}
    >
      <aside className="border-r border-border-soft bg-surface overflow-y-auto">
        {sidebar}
      </aside>
      <main className="flex flex-col min-w-0 overflow-hidden">{main}</main>
      <aside className="border-l border-border-soft bg-surface overflow-y-auto hidden xl:block">
        {context}
      </aside>
    </div>
  );
}
