import type { ReactNode } from "react";

interface Props {
  heading: string;
  count: number;
  children: ReactNode;
}

export function AttentionGroup({ heading, count, children }: Props) {
  return (
    <section className="flex flex-col gap-2">
      <div className="flex items-baseline gap-2">
        <h3 className="text-[13.5px] font-semibold text-text">{heading}</h3>
        <span className="text-[11px] font-mono text-text-dim">{count}</span>
      </div>
      <div className="flex flex-col gap-2">{children}</div>
    </section>
  );
}
