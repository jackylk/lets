import { ContextPane, ContextBlock } from "../layout/ContextPane";
import { GoalAutoPanel } from "./GoalAutoPanel";
import {
  useDiscussionItems,
  DecisionsPanel,
  ConstraintsPanel,
  OpenQuestionsPanel,
  OptionsPanel,
  ReferencesPanel,
  BlindSpotsPanel,
  CritiquesPanel,
  ExtensionsPanel,
} from "./DiscussionPanes";
import { useTopicMessages } from "../api/queries";

interface Props {
  topicId: number;
  projectId: number | null;
}

export function TopicContext({ topicId }: Props) {
  const messages = useTopicMessages(topicId);
  const items = useDiscussionItems(topicId);

  return (
    <ContextPane>
      <ContextBlock label="正在讨论">
        <GoalAutoPanel topicId={topicId} />
      </ContextBlock>

      <ContextBlock
        label="共识"
        right={items.decisions.length > 0 ? `${items.decisions.length}` : undefined}
        hint="这次讨论里达成的结论"
      >
        <DecisionsPanel items={items.decisions} />
      </ContextBlock>

      <ContextBlock
        label="候选方案"
        right={items.options.length > 0 ? `${items.options.length}` : undefined}
        hint="正在比较的几条路线 — 每张卡片带 ✓✗"
      >
        <OptionsPanel items={items.options} />
      </ContextBlock>

      <ContextBlock
        label="待回答"
        right={items.openQuestions.length > 0 ? `${items.openQuestions.length}` : undefined}
        hint="还没想清楚的问题，挂在这里别忘了"
      >
        <OpenQuestionsPanel
          items={items.openQuestions}
          topicId={topicId}
          dismissedCount={items.dismissedCount}
        />
      </ContextBlock>

      <ContextBlock
        label="你没想到的"
        right={items.blindSpots.length > 0 ? `${items.blindSpots.length}` : undefined}
        hint="agent 帮你查漏 — 设计里还没考虑到的角度"
      >
        <BlindSpotsPanel items={items.blindSpots} />
      </ContextBlock>

      <ContextBlock
        label="反方观点"
        right={items.critiques.length > 0 ? `${items.critiques.length}` : undefined}
        hint="agent 唱反调 — 这个方向哪里站不住"
      >
        <CritiquesPanel items={items.critiques} />
      </ContextBlock>

      <ContextBlock
        label="延展想法"
        right={items.extensions.length > 0 ? `${items.extensions.length}` : undefined}
        hint="agent 的 yes-and — 顺着这个方向还可以怎么走"
      >
        <ExtensionsPanel items={items.extensions} />
      </ContextBlock>

      <ContextBlock
        label="约束"
        right={items.constraints.length > 0 ? `${items.constraints.length}` : undefined}
        hint="不能动的条件 — 技术栈 / 截止日期 / 合规要求"
      >
        <ConstraintsPanel items={items.constraints} />
      </ContextBlock>

      <ContextBlock label="图与资料" hint="聊天里出现的 mermaid 图和链接自动收集到这里">
        <ReferencesPanel messages={messages.data?.messages ?? []} topicId={topicId} />
      </ContextBlock>
    </ContextPane>
  );
}
