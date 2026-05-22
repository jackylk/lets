import type { ReactNode } from "react";

export function ContextPane({ children }: { children: ReactNode }) {
  return <div className="flex flex-col gap-3 md:gap-4 p-3 md:p-4">{children}</div>;
}

interface BlockProps { label: string; right?: ReactNode; hint?: string; children: ReactNode }
export function ContextBlock({ label, right, hint, children }: BlockProps) {
  return (
    <div>
      <div className="flex items-baseline justify-between mb-1.5 px-1">
        <span
          className="text-[11px] uppercase tracking-wider font-semibold text-text-dim"
          title={hint}
        >
          {label}
        </span>
        {right && <span className="text-[11px] font-mono text-text-dim">{right}</span>}
      </div>
      {children}
    </div>
  );
}
