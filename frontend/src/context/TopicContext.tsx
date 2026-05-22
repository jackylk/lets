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
      <ContextBlock label="方案输出" hint="导出或分享 agent 持续维护的设计方案">
        <SpecActions topicId={topicId} />
      </ContextBlock>

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

function SpecActions({ topicId }: { topicId: number }) {
  const identity = useIdentity();
  const [busy, setBusy] = useState<"download" | "share" | null>(null);
  const [shareUrl, setShareUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function downloadSpec() {
    setBusy("download");
    setError(null);
    try {
      const res = await fetch(`/api/topics/${topicId}/spec`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `topic-${topicId}-design.md`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  }

  async function shareSpec() {
    setBusy("share");
    setError(null);
    try {
      const data = await apiRequest<{ url: string }>("/api/topics/" + topicId + "/share", {
        method: "POST",
        body: { reuse_existing: true },
        identity,
      });
      setShareUrl(data.url);
      await navigator.clipboard?.writeText(data.url);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="border border-border-soft bg-surface-elev rounded p-2.5 flex flex-col gap-2">
      <div className="flex gap-2">
        <button
          type="button"
          onClick={downloadSpec}
          disabled={busy !== null}
          title="下载当前设计方案 Markdown"
          className="flex-1 px-2.5 py-1.5 rounded-[3px] border border-border-soft text-[12px] text-text-dim hover:text-text hover:border-border disabled:opacity-50"
        >
          {busy === "download" ? "…" : "导出"}
        </button>
        <button
          type="button"
          onClick={shareSpec}
          disabled={busy !== null}
          title="生成公开只读链接并复制"
          className="flex-1 px-2.5 py-1.5 rounded-[3px] border border-border-soft text-[12px] text-text-dim hover:text-text hover:border-border disabled:opacity-50"
        >
          {busy === "share" ? "…" : "分享"}
        </button>
      </div>
      {shareUrl && (
        <a
          href={shareUrl}
          target="_blank"
          rel="noreferrer"
          className="text-[11.5px] font-mono text-text-dim hover:text-text truncate"
          title={shareUrl}
        >
          {shareUrl}
        </a>
      )}
      {error && <div className="text-[11.5px] text-accent-text">失败：{error}</div>}
    </div>
  );
}
