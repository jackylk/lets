import { useTopicTaskTree } from "../api/taskTreeQueries";

interface Props {
  topicId: number;
}

export function GoalDetailPanel({ topicId }: Props) {
  const tree = useTopicTaskTree(topicId);
  if (tree.isLoading || !tree.data) {
    return <div className="text-text-dim text-sm">…</div>;
  }
  if (!tree.data.tree || !tree.data.tree.goal_spec_text) {
    return (
      <div className="border border-dashed border-border rounded p-3 text-center text-text-dim text-sm">
        尚未设定目标
      </div>
    );
  }
  const t = tree.data.tree;
  return (
    <div className="border border-border-soft rounded-lg bg-surface-elev p-3 flex flex-col gap-2">
      <div className="flex items-center gap-2">
        <span className="text-[11px] uppercase tracking-wider text-text-dim font-semibold">
          目标 Artifact
        </span>
        <span className="font-mono text-[11px] text-text-dim ml-auto">
          v{t.version}
        </span>
      </div>
      {t.goal_artifact_id && (
        <div className="font-mono text-[13px]">artifact#{t.goal_artifact_id}</div>
      )}
      <p className="text-[12px] text-text-muted leading-relaxed">
        {t.goal_spec_text}
      </p>
    </div>
  );
}
