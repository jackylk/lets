import { useState } from "react";
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
import { apiRequest } from "../api/client";
import { useIdentity } from "../identity/useIdentity";

interface Props {
  topicId: number;
  projectId: number | null;
}

export function TopicContext({ topicId }: Props) {
  const messages = useTopicMessages(topicId);
  const items = useDiscussionItems(topicId);

  return (
    <ContextPane>
      <div className="px-1 text-[11px] leading-relaxed text-text-dim">
        这里由 agent 自动总结当前话题，方便快速回看上下文。
      </div>

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

      <ContextBlock label="方案输出" hint="打开在线 Spec，并复制可分享链接">
        <SpecActions topicId={topicId} />
      </ContextBlock>
    </ContextPane>
  );
}

function SpecActions({ topicId }: { topicId: number }) {
  const identity = useIdentity();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function openSpec() {
    setBusy(true);
    setError(null);
    try {
      const data = await apiRequest<{ url: string }>("/api/topics/" + topicId + "/share", {
        method: "POST",
        body: { reuse_existing: true },
        identity,
      });
      await navigator.clipboard?.writeText(data.url);
      window.open(data.url, "_blank", "noopener,noreferrer");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="border border-border-soft bg-surface-elev rounded p-2.5 flex flex-col gap-2">
      <button
        type="button"
        onClick={openSpec}
        disabled={busy}
        title="打开在线 Spec，并复制可分享链接；页面内可下载 Markdown"
        className="w-full px-2.5 py-1.5 rounded-[3px] border border-border-soft text-[12px] text-text-dim hover:text-text hover:border-border disabled:opacity-50"
      >
        {busy ? "打开中…" : "Spec"}
      </button>
      <div className="text-[11px] leading-snug text-text-dim">
        打开在线页并复制共享链接；页面内可下载 Markdown。
      </div>
      {error && <div className="text-[11.5px] text-accent-text">失败：{error}</div>}
    </div>
  );
}
