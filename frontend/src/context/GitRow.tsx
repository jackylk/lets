interface Props {
  subject: string;
  shortSha: string;
  author?: string;
  dirtyCount: number;
}

export function GitRow({ subject, shortSha, author, dirtyCount }: Props) {
  return (
    <div className="flex flex-col gap-1 text-[12px] text-text-muted">
      <div className="flex items-center gap-2">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="6" cy="6" r="3" />
          <circle cx="6" cy="18" r="3" />
          <circle cx="18" cy="12" r="3" />
          <path d="M6 9v6" />
          <path d="M9 18h6a3 3 0 0 0 3-3" />
        </svg>
        <span className="font-mono text-[11px] text-text-dim">{shortSha}</span>
        <span className="truncate">{subject}</span>
      </div>
      <div className="text-[11px] text-text-dim font-mono pl-5">
        {author && <>by {author} · </>}
        {dirtyCount > 0 ? `${dirtyCount} dirty` : "clean"}
      </div>
    </div>
  );
}
