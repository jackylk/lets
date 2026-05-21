import { useMemo } from "react";
import { useTopicMessages, useArtifactsByTopic } from "../api/queries";
import { cn } from "../lib/cn";

interface Props {
  topicId: number;
}

interface Step {
  id: string;
  label: string;
  detail: string;
  status: "done" | "doing" | "queued";
  actor: string;
}

/**
 * Derives a task timeline from the typed message stream so the user
 * sees what's been done in this topic at a glance. No backend table
 * required — purely a projection over messages + artifacts.
 *
 * Rules:
 *   - status (active)  → "<actor> 工作中: <body>"   (doing) — supersedes earlier doing
 *   - artifact_revision → "<actor> 交付 vN"         (done)
 *   - review            → "<actor> 评审"            (done)
 *   - finding           → "<actor> 完工"            (done)
 *   - artifact w/o follow-up review → "等待评审"     (queued)
 */
export function ActivityTimelinePanel({ topicId }: Props) {
  const messages = useTopicMessages(topicId);
  const artifacts = useArtifactsByTopic(topicId);
  const msgs = messages.data?.messages ?? [];

  const steps: Step[] = useMemo(() => {
    const out: Step[] = [];
    let currentlyWorking: string | null = null;
    let pendingReview = false;
    let pendingReviewActor = "";

    function actorLabel(typeOk: "human" | "agent", id: number | null) {
      if (id === null) return "system";
      // Build a quick lookup from the messages themselves — actors that
      // posted in this topic.
      const msg = msgs.find(
        (m) => m.actor_id === id && m.actor_type === typeOk,
      );
      if (!msg) return typeOk === "human" ? `human#${id}` : `agent#${id}`;
      return typeOk === "human" ? "human" : "agent";
    }

    for (const m of msgs) {
      const actor = m.actor_type === "agent" ? "agent" : "human";
      const _ = actorLabel; void _;
      if (m.type === "status") {
        currentlyWorking = m.body.slice(0, 80);
        out.push({
          id: `m-${m.id}`,
          label: "开始执行",
          detail: m.body.slice(0, 80),
          status: "doing",
          actor,
        });
      } else if (m.type === "artifact_revision") {
        const meta = m.metadata as { version?: string } | undefined;
        const label = meta?.version ? `交付 ${meta.version}` : "交付一版";
        out.push({
          id: `m-${m.id}`,
          label,
          detail: m.body.slice(0, 80),
          status: "done",
          actor,
        });
        currentlyWorking = null;
        pendingReview = true;
        pendingReviewActor = actor;
      } else if (m.type === "review") {
        out.push({
          id: `m-${m.id}`,
          label: "评审完成",
          detail: m.body.slice(0, 80),
          status: "done",
          actor,
        });
        pendingReview = false;
      } else if (m.type === "finding") {
        out.push({
          id: `m-${m.id}`,
          label: "完工",
          detail: m.body.slice(0, 80),
          status: "done",
          actor,
        });
        currentlyWorking = null;
      }
    }

    if (currentlyWorking) {
      // Most recent status is unresolved
      out.push({
        id: "queued-working",
        label: "进行中",
        detail: currentlyWorking,
        status: "doing",
        actor: "—",
      });
    } else if (pendingReview) {
      out.push({
        id: "queued-review",
        label: "等待评审",
        detail: "刚交付一版，还没有评审消息",
        status: "queued",
        actor: pendingReviewActor,
      });
    }
    return out;
  }, [msgs]);

  if (messages.isLoading) {
    return <div className="text-text-dim text-sm">…</div>;
  }
  if (steps.length === 0) {
    return (
      <div className="border border-dashed border-border rounded p-3 text-center text-text-dim text-sm">
        尚无活动
      </div>
    );
  }

  const doneCount = steps.filter((s) => s.status === "done").length;
  const artifactCount = artifacts.data?.length ?? 0;

  return (
    <div className="border border-border-soft rounded bg-surface-elev p-3 flex flex-col gap-2 shadow-sm">
      <div className="flex items-baseline justify-between">
        <span className="font-semibold text-[13px]">
          活动时间线
        </span>
        <span className="font-mono text-[11px] text-text-dim">
          {doneCount} / {steps.length} done · {artifactCount} 交付物
        </span>
      </div>
      <ol className="flex flex-col gap-1.5">
        {steps.map((s) => (
          <li key={s.id} className="flex items-start gap-2 text-[12.5px]">
            <span
              className={cn(
                "inline-block w-3.5 h-3.5 rounded-full mt-px shrink-0 border",
                s.status === "done" && "border-finding bg-finding",
                s.status === "doing" && "border-status-work bg-status-work animate-pulse",
                s.status === "queued" && "border-border bg-bg",
              )}
              aria-label={s.status}
            />
            <div className="min-w-0 flex-1">
              <div className="flex items-baseline gap-2">
                <span className="font-medium truncate">{s.label}</span>
                <span className="font-mono text-[10px] text-text-dim shrink-0">
                  {s.actor}
                </span>
              </div>
              <div className="text-[11.5px] text-text-muted truncate">
                {s.detail}
              </div>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
