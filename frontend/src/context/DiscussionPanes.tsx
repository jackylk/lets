import { useMemo, useState } from "react";
import { useTopicMessages } from "../api/queries";
import type { MessageDTO } from "../api/types";
import { jumpToMessage } from "./jumpToMessage";
import { ResolveQuestionInline } from "./ResolveQuestionInline";
import { useDismissedQuestions } from "./useDismissedQuestions";
import { openDiagram } from "../messages/openDiagram";

/**
 * Right-pane panels for the proposal-discussion scenario. Each panel is a
 * pure projection over the topic's typed messages — the source of truth is
 * the chat stream itself, the panels never own state.
 *
 * Convention: items here come from messages whose
 *   metadata.discussion_kind ∈ {"decision","option","constraint","open_question"}
 * Agents (or humans via `/decision` etc.) post them as typed messages of
 * type `decision` / `proactive_finding` / `question` etc. — the
 * discussion_kind tag is the routing label.
 *
 * In Slice 1 nothing posts these tags yet, so the panels render empty
 * states. Slice 2 wires the agent prompt + UI promote chips to fill them.
 */

type DiscussionKind =
  | "decision"
  | "option"
  | "constraint"
  | "open_question"
  | "blind_spot"
  | "critique"
  | "extension";

interface DiscussionItem {
  id: number;
  kind: DiscussionKind;
  title?: string;
  body: string;
  pros?: string[];
  cons?: string[];
  posted_by_agent: boolean;
  created_at: string;
  /** Source message this item was promoted from (jump-target). */
  promoted_from?: number;
  /** When this is a decision answering an open_question, the question body. */
  answers_question?: string;
}

function sourceText(item: DiscussionItem): string {
  const author = item.posted_by_agent ? "agent 总结" : "人手动加入";
  const source =
    item.promoted_from && item.promoted_from !== item.id
      ? `点击看来源 #${item.promoted_from}`
      : "点击看本条记录";
  return `${author} · ${source}`;
}

function SourceMeta({ item }: { item: DiscussionItem }) {
  return (
    <span className="text-[10.5px] leading-snug text-text-dim">
      {sourceText(item)}
    </span>
  );
}

function ItemBodyWithSource({ item }: { item: DiscussionItem }) {
  return (
    <span className="min-w-0 flex flex-col gap-1">
      <span>{item.body}</span>
      <SourceMeta item={item} />
    </span>
  );
}

function asKind(meta: unknown): DiscussionKind | null {
  if (typeof meta !== "object" || meta === null) return null;
  const k = (meta as Record<string, unknown>).discussion_kind;
  if (
    k === "decision" ||
    k === "option" ||
    k === "constraint" ||
    k === "open_question" ||
    k === "blind_spot" ||
    k === "critique" ||
    k === "extension"
  ) {
    return k;
  }
  return null;
}

function projectItems(messages: MessageDTO[]): DiscussionItem[] {
  // First pass: index every open_question body by id, so we can attach the
  // question text to its resolving decision later (otherwise "GUI" alone
  // is meaningless in 共识).
  const questionBodyById = new Map<number, string>();
  for (const m of messages) {
    const meta = m.metadata as Record<string, unknown> | null;
    if (meta?.discussion_kind === "open_question") {
      questionBodyById.set(m.id, m.body);
    }
  }

  const out: DiscussionItem[] = [];
  for (const m of messages) {
    const kind = asKind(m.metadata);
    if (!kind) continue;
    const meta = m.metadata as Record<string, unknown>;
    // promoted_from may be missing for legacy items; jump falls back to the
    // pane item's own id in that case (still useful — scrolls to where the
    // typed message lives in the stream).
    const promotedFrom =
      typeof meta.promoted_from === "number" ? meta.promoted_from : m.id;
    const answersQid =
      typeof meta.resolves_question === "number"
        ? meta.resolves_question
        : null;
    out.push({
      id: m.id,
      kind,
      title: typeof meta.title === "string" ? meta.title : undefined,
      body: m.body,
      pros: Array.isArray(meta.pros) ? (meta.pros as string[]) : undefined,
      cons: Array.isArray(meta.cons) ? (meta.cons as string[]) : undefined,
      posted_by_agent: m.actor_type === "agent",
      created_at: m.created_at,
      promoted_from: promotedFrom,
      answers_question:
        answersQid !== null ? questionBodyById.get(answersQid) : undefined,
    });
  }
  return out;
}

export function useDiscussionItems(topicId: number): {
  loading: boolean;
  decisions: DiscussionItem[];
  options: DiscussionItem[];
  constraints: DiscussionItem[];
  openQuestions: DiscussionItem[];
  dismissedCount: number;
  blindSpots: DiscussionItem[];
  critiques: DiscussionItem[];
  extensions: DiscussionItem[];
} {
  const messages = useTopicMessages(topicId);
  const { dismissed } = useDismissedQuestions(topicId);
  return useMemo(() => {
    const rawMessages = messages.data?.messages ?? [];
    const items = projectItems(rawMessages);

    // Find which question ids have been resolved (a decision exists with
    // metadata.resolves_question === q.id). Those questions drop out of
    // the 待回答 panel and the answering decision shows up in 共识.
    const resolvedQuestionIds = new Set<number>();
    for (const m of rawMessages) {
      const meta = m.metadata as Record<string, unknown> | null;
      if (!meta) continue;
      if (meta.discussion_kind !== "decision") continue;
      if (typeof meta.resolves_question === "number") {
        resolvedQuestionIds.add(meta.resolves_question);
      }
    }

    const openQuestionsAll = items.filter(
      (i) => i.kind === "open_question" && !resolvedQuestionIds.has(i.id),
    );
    const openQuestions = openQuestionsAll.filter((i) => !dismissed.has(i.id));
    const dismissedCount = openQuestionsAll.length - openQuestions.length;

    return {
      loading: messages.isLoading,
      decisions: items.filter((i) => i.kind === "decision"),
      options: items.filter((i) => i.kind === "option"),
      constraints: items.filter((i) => i.kind === "constraint"),
      openQuestions,
      dismissedCount,
      blindSpots: items.filter((i) => i.kind === "blind_spot"),
      critiques: items.filter((i) => i.kind === "critique"),
      extensions: items.filter((i) => i.kind === "extension"),
    };
  }, [messages.data, messages.isLoading, dismissed]);
}

function EmptyState({ children }: { children: string }) {
  return (
    <div className="border border-dashed border-border rounded p-3 text-center text-text-dim text-[12px] italic">
      {children}
    </div>
  );
}

function DotItem({ item, accent }: { item: DiscussionItem; accent: string }) {
  const jumpId = item.promoted_from ?? item.id;
  return (
    <button
      type="button"
      onClick={() => jumpToMessage(jumpId)}
      title="点击跳到对应的对话上下文"
      className="bg-surface-elev border border-border-soft rounded p-2.5 text-[13px] leading-relaxed flex gap-2 items-start text-left hover:bg-surface-hover hover:border-accent-border transition-colors w-full"
    >
      <span
        aria-hidden
        className="w-1.5 h-1.5 rounded-full flex-shrink-0 mt-[7px]"
        style={{ background: accent }}
      />
      <ItemBodyWithSource item={item} />
    </button>
  );
}

function DecisionItem({ item }: { item: DiscussionItem }) {
  const jumpId = item.promoted_from ?? item.id;
  const hasQuestion = !!item.answers_question;
  return (
    <button
      type="button"
      onClick={() => jumpToMessage(jumpId)}
      title="点击跳到对应的对话上下文"
      className="bg-surface-elev border border-border-soft rounded p-2.5 text-[13px] leading-relaxed flex flex-col gap-1 text-left hover:bg-surface-hover hover:border-accent-border transition-colors w-full"
    >
      {hasQuestion && (
        <div className="text-[11.5px] text-text-dim italic line-clamp-2 leading-snug">
          {item.answers_question}
        </div>
      )}
      <div className="flex gap-2 items-start">
        <span
          aria-hidden
          className="w-1.5 h-1.5 rounded-full flex-shrink-0 mt-[7px]"
          style={{ background: "var(--color-finding)" }}
        />
        <span className="min-w-0">
          {hasQuestion && (
            <span className="font-mono text-[10.5px] uppercase tracking-[0.04em] text-text-dim mr-1.5">
              →
            </span>
          )}
          {item.body}
        </span>
      </div>
      <SourceMeta item={item} />
    </button>
  );
}

export function DecisionsPanel({ items }: { items: DiscussionItem[] }) {
  if (items.length === 0) return <EmptyState>聊到「就这么定了」时点 agent 消息下的 [+ 共识] 收进来</EmptyState>;
  return (
    <div className="flex flex-col gap-2">
      {items.map((i) => (
        <DecisionItem key={i.id} item={i} />
      ))}
    </div>
  );
}

/**
 * 你没想到的: design blind spots the agent flags — risks, stakeholders,
 * second-order effects the human/design hasn't considered. Visually
 * distinct (warning tone) so they stand out from the steady-state panels.
 */
export function BlindSpotsPanel({ items }: { items: DiscussionItem[] }) {
  if (items.length === 0)
    return <EmptyState>agent 发现设计里没考虑到的点会冒到这里</EmptyState>;
  return (
    <div className="flex flex-col gap-2">
      {items.map((i) => {
        const jumpId = i.promoted_from ?? i.id;
        return (
          <button
            type="button"
            key={i.id}
            onClick={() => jumpToMessage(jumpId)}
            title="点击跳到 agent 提出这个盲点的那条消息"
            className="bg-surface-elev border border-dashed border-accent-border rounded p-2.5 text-[13px] leading-relaxed flex gap-2 items-start text-left hover:bg-surface-hover transition-colors w-full"
          >
            <span
              aria-hidden
              className="font-mono text-[10px] uppercase tracking-[0.04em] text-accent-text border border-accent-border px-1 rounded shrink-0 mt-[2px]"
            >
              漏
            </span>
            <span className="min-w-0 text-text">
              <ItemBodyWithSource item={i} />
            </span>
          </button>
        );
      })}
    </div>
  );
}

export function ConstraintsPanel({ items }: { items: DiscussionItem[] }) {
  if (items.length === 0) return <EmptyState>记下技术栈 / 截止日期 / 合规等限制条件</EmptyState>;
  return (
    <div className="flex flex-col gap-2">
      {items.map((i) => (
        <DotItem key={i.id} item={i} accent="var(--color-handoff)" />
      ))}
    </div>
  );
}

export function OpenQuestionsPanel({
  items,
  topicId,
  dismissedCount,
}: {
  items: DiscussionItem[];
  topicId: number;
  dismissedCount: number;
}) {
  const { restoreAll } = useDismissedQuestions(topicId);
  if (items.length === 0 && dismissedCount === 0)
    return <EmptyState>有疑问就挂在这里 — 不用每条都答</EmptyState>;
  return (
    <div className="flex flex-col gap-2">
      {items.map((i) => (
        <OpenQuestionItem key={i.id} item={i} topicId={topicId} />
      ))}
      {dismissedCount > 0 && (
        <div className="flex items-center justify-between text-[11px] text-text-dim pt-1">
          <span>{dismissedCount} 条已略过</span>
          <button
            type="button"
            onClick={restoreAll}
            className="hover:text-accent-text underline-offset-2 hover:underline"
          >
            恢复显示
          </button>
        </div>
      )}
    </div>
  );
}

function OpenQuestionItem({ item, topicId }: { item: DiscussionItem; topicId: number }) {
  const [answering, setAnswering] = useState(false);
  const { dismiss } = useDismissedQuestions(topicId);
  const jumpId = item.promoted_from ?? item.id;
  return (
    <div className="bg-surface-elev border border-border-soft rounded p-2.5 flex flex-col gap-1.5">
      <div className="flex gap-2 items-start text-[13px] leading-relaxed">
        <button
          type="button"
          onClick={() => jumpToMessage(jumpId)}
          title="点击跳到对应的对话上下文"
          className="flex gap-2 items-start text-left flex-1 min-w-0 hover:text-accent-text"
        >
          <span
            aria-hidden
            className="w-1.5 h-1.5 rounded-full flex-shrink-0 mt-[7px]"
            style={{ background: "var(--color-accent)" }}
          />
          <ItemBodyWithSource item={item} />
        </button>
        {!answering && (
          <div className="flex items-center gap-1.5 shrink-0">
            <button
              type="button"
              onClick={() => setAnswering(true)}
              className="text-[10.5px] font-mono uppercase tracking-[0.04em] text-text-dim hover:text-accent-text"
              title="把这条问题的答案记为共识，从待回答移除"
            >答</button>
            <button
              type="button"
              onClick={() => dismiss(item.id)}
              className="text-[10.5px] font-mono uppercase tracking-[0.04em] text-text-dim hover:text-text"
              title="先不答 — 从待回答移除，仍可在底部「恢复显示」里找回"
            >略</button>
          </div>
        )}
      </div>
      {answering && (
        <ResolveQuestionInline
          topicId={topicId}
          questionId={item.id}
          questionBody={item.body}
          onDone={() => setAnswering(false)}
        />
      )}
    </div>
  );
}

/**
 * 反方 (critique): devil's-advocate objections to the current direction.
 * Visually similar to 你没想到的 but with a "反" tag so the user can tell
 * them apart — these are reasoned dissent rather than just gaps.
 */
export function CritiquesPanel({ items }: { items: DiscussionItem[] }) {
  if (items.length === 0)
    return <EmptyState>agent 对当前方案的反方观点会冒到这里</EmptyState>;
  return (
    <div className="flex flex-col gap-2">
      {items.map((i) => {
        const jumpId = i.promoted_from ?? i.id;
        return (
          <button
            type="button"
            key={i.id}
            onClick={() => jumpToMessage(jumpId)}
            title="点击跳到 agent 提出反方观点的那条消息"
            className="bg-surface-elev border border-border-soft rounded p-2.5 text-[13px] leading-relaxed flex gap-2 items-start text-left hover:bg-surface-hover hover:border-accent-border transition-colors w-full"
          >
            <span
              aria-hidden
              className="font-mono text-[10px] uppercase tracking-[0.04em] text-accent-text bg-accent-soft px-1 rounded shrink-0 mt-[2px]"
            >
              反
            </span>
            <span className="min-w-0 text-text">
              <ItemBodyWithSource item={i} />
            </span>
          </button>
        );
      })}
    </div>
  );
}

/**
 * 延展 (extension): "yes-and" creative variations or adjacent ideas.
 */
export function ExtensionsPanel({ items }: { items: DiscussionItem[] }) {
  if (items.length === 0)
    return <EmptyState>agent 的"yes-and"延展想法会冒到这里</EmptyState>;
  return (
    <div className="flex flex-col gap-2">
      {items.map((i) => {
        const jumpId = i.promoted_from ?? i.id;
        return (
          <button
            type="button"
            key={i.id}
            onClick={() => jumpToMessage(jumpId)}
            title="点击跳到 agent 提出这个延展想法的那条消息"
            className="bg-surface-elev border border-border-soft rounded p-2.5 text-[13px] leading-relaxed flex gap-2 items-start text-left hover:bg-surface-hover hover:border-accent-border transition-colors w-full"
          >
            <span
              aria-hidden
              className="font-mono text-[10px] uppercase tracking-[0.04em] text-finding bg-finding-bg px-1 rounded shrink-0 mt-[2px]"
            >
              延
            </span>
            <span className="min-w-0 text-text">
              <ItemBodyWithSource item={i} />
            </span>
          </button>
        );
      })}
    </div>
  );
}

export function OptionsPanel({ items }: { items: DiscussionItem[] }) {
  if (items.length === 0) return <EmptyState>2-4 个备选方向放这里，方便比较</EmptyState>;
  return (
    <div className="flex flex-col gap-2">
      {items.map((i) => {
        const jumpId = i.promoted_from ?? i.id;
        return (
          <button
            type="button"
            key={i.id}
            onClick={() => jumpToMessage(jumpId)}
            title="点击跳到对应的对话上下文"
            className="bg-surface-elev border border-border-soft rounded p-3 flex flex-col gap-1.5 text-left hover:bg-surface-hover hover:border-accent-border transition-colors w-full"
          >
            <div className="font-[var(--font-display)] font-semibold text-[14px]">
              {i.title || i.body.slice(0, 40)}
            </div>
            {(i.pros?.length || i.cons?.length) && (
              <div className="text-[12px] flex flex-col gap-0.5">
                {i.pros?.map((p, j) => (
                  <span key={`p-${j}`} className="text-status-on">✓ {p}</span>
                ))}
                {i.cons?.map((c, j) => (
                  <span key={`c-${j}`} className="text-accent-text">✗ {c}</span>
                ))}
              </div>
            )}
            {!i.pros?.length && !i.cons?.length && i.title && (
              <div className="text-[12.5px] text-text-muted leading-relaxed">{i.body}</div>
            )}
            <SourceMeta item={i} />
          </button>
        );
      })}
    </div>
  );
}

/**
 * 图与资料: auto-collected ```mermaid``` blocks and URLs from chat messages.
 */
export function ReferencesPanel({ messages, topicId }: { messages: MessageDTO[]; topicId: number }) {
  const items = useMemo(() => {
    type Ref =
      | { kind: "diagram"; label: string; source: string; from_msg_id: number }
      | { kind: "link"; label: string; from_msg_id: number };
    const out: Ref[] = [];
    for (const m of messages) {
      if (m.type !== "chat" && m.type !== "finding") continue;
      // mermaid blocks — carry full source so the overlay can render it.
      const mermaidMatches = m.body.matchAll(/```mermaid\s+([\s\S]*?)```/g);
      for (const mm of mermaidMatches) {
        const body = mm[1] || "";
        const first = body.trim().split("\n")[0]?.trim() ?? "diagram";
        out.push({
          kind: "diagram",
          label: first.slice(0, 30) || "diagram",
          source: body,
          from_msg_id: m.id,
        });
      }
      // URLs
      const urlMatches = m.body.matchAll(/https?:\/\/[^\s)>'"]+/g);
      for (const u of urlMatches) {
        out.push({ kind: "link", label: u[0], from_msg_id: m.id });
      }
    }
    return out;
  }, [messages]);

  if (items.length === 0) return <EmptyState>聊天里出现的图和链接会自动收到这里</EmptyState>;

  return (
    <div className="flex flex-col gap-1.5">
      {items.map((r, i) => {
        const onClick =
          r.kind === "link"
            ? () => window.open(r.label, "_blank", "noopener,noreferrer")
            : () =>
                openDiagram({
                  source: r.source,
                  fromMsgId: r.from_msg_id,
                  label: r.label,
                  topicId,
                });
        return (
          <button
            type="button"
            key={`${r.from_msg_id}-${i}`}
            onClick={onClick}
            title={r.kind === "diagram" ? "点击放大查看（可跳回原消息）" : "在新标签页打开链接"}
            className="flex items-center gap-2 px-2.5 py-1.5 bg-surface-elev border border-border-soft rounded text-[12.5px] hover:bg-surface-hover hover:border-accent-border transition-colors w-full text-left"
          >
            <span className="font-mono text-[10px] uppercase tracking-[0.04em] text-text-dim border border-border-soft px-1.5 py-px rounded shrink-0">
              {r.kind === "diagram" ? "图" : "链接"}
            </span>
            <span className="text-text truncate min-w-0">{r.label}</span>
          </button>
        );
      })}
    </div>
  );
}
