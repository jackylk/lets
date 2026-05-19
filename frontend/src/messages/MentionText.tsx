import type { ReactNode } from "react";

const MENTION_RE = /(@[\p{L}\p{N}_-]+)/gu;

export function MentionText({ children }: { children: string }) {
  const parts = children.split(MENTION_RE);
  const out: ReactNode[] = [];
  for (let i = 0; i < parts.length; i++) {
    const p = parts[i];
    if (p === undefined) continue;
    if (MENTION_RE.test(p)) {
      out.push(
        <span key={i} className="mention bg-accent-soft text-accent-text px-1 rounded font-mono text-[12px]">
          {p}
        </span>,
      );
    } else if (p) {
      out.push(<span key={i}>{p}</span>);
    }
    MENTION_RE.lastIndex = 0;
  }
  return <>{out}</>;
}
