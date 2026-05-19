interface Props {
  artifactName: string;
  artifactVersion: string;
  spec: string;
  approvers: string[];
  onMarkFinal: () => void;
  onProposeChange: () => void;
}

export function GoalDetailPanel({ artifactName, artifactVersion, spec, approvers, onMarkFinal, onProposeChange }: Props) {
  return (
    <div className="border border-border-soft rounded-lg bg-surface-elev p-3 flex flex-col gap-2">
      <div className="flex items-center gap-2">
        <span className="text-[11px] uppercase tracking-wider text-text-dim font-semibold">目标 Artifact</span>
        <span className="bg-artifact text-bg px-1.5 py-px rounded text-[10px] font-mono ml-auto">{artifactVersion}</span>
      </div>
      <div className="font-mono text-[13px]">{artifactName}</div>
      <p className="text-[12px] text-text-muted leading-relaxed">{spec}</p>
      <div className="flex flex-wrap gap-1 mt-1">
        <span className="text-[11px] text-text-muted">approvers:</span>
        {approvers.map((a) => (
          <span key={a} className="text-[11px] font-mono px-1.5 py-px bg-surface rounded">{a}</span>
        ))}
      </div>
      <div className="flex gap-2 mt-1">
        <button
          type="button"
          onClick={onMarkFinal}
          className="flex-1 px-2 py-1 rounded bg-text text-bg text-[12px] font-medium"
        >
          Mark as Final
        </button>
        <button
          type="button"
          onClick={onProposeChange}
          className="px-2 py-1 rounded border border-border text-[12px]"
          title="提议修改目标会发起一条 goal_proposal 消息"
        >
          提议修改
        </button>
      </div>
    </div>
  );
}
