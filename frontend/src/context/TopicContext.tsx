import { useMemo } from "react";
import { ContextPane, ContextBlock } from "../layout/ContextPane";
import { TopicInfoCard } from "./TopicInfoCard";
import { GoalAutoPanel } from "./GoalAutoPanel";
import { ActivityTimelinePanel } from "./ActivityTimelinePanel";
import { TaskTreePanel } from "./TaskTreePanel";
import { ArtifactPanel } from "./ArtifactPanel";
import { SpecTouchedPanel } from "./SpecTouchedPanel";
import { ParticipantsPanel } from "./ParticipantsPanel";
import { GitRow } from "./GitRow";
import {
  useTopic, useTopicMessages, useTopicParticipants,
  useArtifactsByTopic, useProjectGitStatus,
} from "../api/queries";
import type { SpecChangeMeta } from "../api/types";

interface Props {
  topicId: number;
  projectId: number | null;
}

export function TopicContext({ topicId, projectId }: Props) {
  const topic = useTopic(topicId);
  const messages = useTopicMessages(topicId);
  const participants = useTopicParticipants(topicId);
  const artifacts = useArtifactsByTopic(topicId);
  const gitStatus = useProjectGitStatus(projectId);

  // Derive "spec touched" from spec_change messages in this topic.
  const specItems = useMemo(() => {
    const msgs = messages.data?.messages ?? [];
    const byPath = new Map<
      string,
      { path: string; latestMessageId: number; meta: SpecChangeMeta }
    >();
    for (const m of msgs) {
      if (m.type !== "spec_change") continue;
      const meta = m.metadata as unknown as SpecChangeMeta;
      if (!meta?.file) continue;
      const prev = byPath.get(meta.file);
      if (!prev || m.id > prev.latestMessageId) {
        byPath.set(meta.file, { path: meta.file, latestMessageId: m.id, meta });
      }
    }
    return [...byPath.values()].map((row) => ({
      path: row.path,
      version: row.meta.after !== undefined ? "pending" : "applied",
      pending: row.meta.after !== undefined,
    }));
  }, [messages.data]);

  const participantsList = useMemo(() => {
    const p = participants.data;
    if (!p) return [];
    type Kind = "human" | "claude" | "codex" | "system";
    const out: Array<{ kind: Kind; initial: string; name: string }> = [];
    for (const h of p.humans) {
      out.push({ kind: "human", initial: h.name.slice(0, 1).toUpperCase(), name: h.name });
    }
    for (const a of p.agents) {
      const kind: Kind =
        a.role === "claude" ? "claude" : a.role === "codex" ? "codex" : "system";
      out.push({
        kind,
        initial: a.role === "codex" ? "CX" : "CC",
        name: `${a.role} · ${a.device_label}`,
      });
    }
    return out;
  }, [participants.data]);

  const artifactsList = artifacts.data ?? [];

  return (
    <ContextPane>
      <ContextBlock label="当前 Topic">
        {topic.data ? (
          <TopicInfoCard
            topicSlug={topic.data.slug}
            title={topic.data.title}
            description={`project_id=${topic.data.project_id ?? "—"}`}
            chips={[`#${topic.data.id}`, "live"]}
          />
        ) : (
          <div className="text-text-dim text-sm">…</div>
        )}
      </ContextBlock>

      <ContextBlock label="目标">
        <GoalAutoPanel topicId={topicId} />
      </ContextBlock>

      <ContextBlock label="方案探索">
        <TaskTreePanel topicId={topicId} />
      </ContextBlock>

      <ContextBlock label="活动">
        <ActivityTimelinePanel topicId={topicId} />
      </ContextBlock>

      <ContextBlock
        label="交付物"
        right={artifactsList.length > 0 ? `${artifactsList.length} 个` : undefined}
      >
        {artifactsList.length === 0 ? (
          <div className="text-text-dim text-sm italic">尚无交付物</div>
        ) : (
          <ArtifactPanel artifacts={artifactsList} />
        )}
      </ContextBlock>

      <ContextBlock label="本 Topic 涉及 Spec">
        {specItems.length === 0 ? (
          <div className="text-text-dim text-sm italic">no spec_change posted</div>
        ) : (
          <SpecTouchedPanel items={specItems} />
        )}
      </ContextBlock>

      <ContextBlock
        label="Participants"
        right={participantsList.length > 0 ? `${participantsList.length}` : undefined}
      >
        {participantsList.length === 0 ? (
          <div className="text-text-dim text-sm italic">no participants yet</div>
        ) : (
          <ParticipantsPanel participants={participantsList} />
        )}
      </ContextBlock>

      <ContextBlock label="Git">
        {gitStatus.data ? (
          <GitRow
            subject={gitStatus.data.head.subject}
            shortSha={gitStatus.data.head.short_sha}
            author={gitStatus.data.head.author}
            dirtyCount={gitStatus.data.dirty.length}
          />
        ) : (
          <div className="text-text-dim text-sm italic">
            {projectId === null ? "no project" : "no repo_path configured"}
          </div>
        )}
      </ContextBlock>
    </ContextPane>
  );
}
