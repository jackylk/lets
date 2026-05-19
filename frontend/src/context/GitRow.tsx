interface Props { branch: string; ahead: number; pendingSpec: boolean }
export function GitRow({ branch, ahead, pendingSpec }: Props) {
  return (
    <div className="flex items-center gap-2 text-[12px] text-text-muted">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="6" cy="6" r="3"/>
        <circle cx="6" cy="18" r="3"/>
        <circle cx="18" cy="12" r="3"/>
        <path d="M6 9v6"/>
        <path d="M9 18h6a3 3 0 0 0 3-3"/>
      </svg>
      <span><span className="font-mono">{branch}</span> · {ahead} ahead{pendingSpec ? " · spec change pending" : ""}</span>
    </div>
  );
}
