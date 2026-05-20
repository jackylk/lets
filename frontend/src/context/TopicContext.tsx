import { ContextPane, ContextBlock } from "../layout/ContextPane";
import { TopicInfoCard } from "./TopicInfoCard";
import { GoalDetailPanel } from "./GoalDetailPanel";
import { TaskTreePanel } from "./TaskTreePanel";
import { ArtifactPanel } from "./ArtifactPanel";
import { SpecTouchedPanel } from "./SpecTouchedPanel";
import { ParticipantsPanel } from "./ParticipantsPanel";
import { GitRow } from "./GitRow";

export function TopicContext() {
  return (
    <ContextPane>
      <ContextBlock label="当前 Topic">
        <TopicInfoCard
          topicSlug="T-PPT"
          title="为 Agent 记忆写一个研讨 PPT"
          description="下周三 AI 研讨会 30min talk · 技术受众 · 主讲 Neo"
          chips={["exploratory", "3 agents", "talk-prep"]}
        />
      </ContextBlock>

      <ContextBlock label="目标">
        <GoalDetailPanel
          artifactName="ai-memory-talk.pptx"
          artifactVersion="v3"
          spec="30 分钟 talk · 技术受众 · 突出「事件性记忆 vs 语义记忆」差异化"
          approvers={["Trinity", "Morpheus", "Neo"]}
          onMarkFinal={() => {}}
          onProposeChange={() => {}}
        />
      </ContextBlock>

      <ContextBlock label="目标分解">
        <TaskTreePanel topicId={1} />
      </ContextBlock>

      <ContextBlock label="Artifact" right="v2 · in-progress">
        <ArtifactPanel
          artifactName="ai-memory-talk.pptx"
          currentVersion="v2"
          versions={["v0", "v1", "v2"]}
          totalSlides={9}
        />
      </ContextBlock>

      <ContextBlock label="本 Topic 涉及 Spec">
        <SpecTouchedPanel
          items={[
            { path: ".claude/skills/research-talk-style", version: "v2 → v3", pending: true },
            { path: ".claude/skills/pptx", version: "v5", pending: false },
          ]}
        />
      </ContextBlock>

      <ContextBlock label="Participants · 6">
        <ParticipantsPanel
          participants={[
            { kind: "human", initial: "N", name: "Neo" },
            { kind: "human", initial: "T", name: "Trinity" },
            { kind: "human", initial: "M", name: "Morpheus" },
            { kind: "claude", initial: "CC", name: "claude · neo-mbp" },
            { kind: "codex", initial: "CX", name: "codex · neo-mbp" },
          ]}
        />
      </ContextBlock>

      <ContextBlock label="Git">
        <GitRow branch="master" ahead={2} pendingSpec />
      </ContextBlock>
    </ContextPane>
  );
}
