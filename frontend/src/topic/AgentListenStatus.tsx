import { useEffect, useMemo, useState } from "react";
import type { MessageDTO, WorkspaceMember } from "../api/types";
import { agentShortName } from "../agent/display";
import { parseBackendTs } from "../lib/time";

interface Props {
  messages: MessageDTO[];
  workspaceMembers?: WorkspaceMember[];
  /** Optional: handle clicking "↓ N 条未读" — defaults to scrolling to first unread. */
  onJumpToUnread?: () => void;
}

function ago(iso: string): string {
  const d = parseBackendTs(iso);
  const secs = Math.max(0, (Date.now() - d.getTime()) / 1000);
  if (secs < 5) return "刚刚";
  if (secs < 60) return `${Math.round(secs)} 秒前`;
  const m = secs / 60;
  if (m < 60) return `${Math.round(m)} 分钟前`;
  const h = m / 60;
  if (h < 24) return `${Math.round(h)} 小时前`;
  return `${Math.round(h / 24)} 天前`;
}

function secsSince(iso: string): number {
  return Math.max(0, (Date.now() - parseBackendTs(iso).getTime()) / 1000);
}

// Mirror gateway's debounce windows (app/gateway.py QUIET_WINDOW_NORMAL / URGENT).
// We use this to count DOWN from "user just posted" to the moment the gateway
// will actually fire claude. After that, real "思考中" status arrives over SSE.
const DEBOUNCE_WINDOW_NORMAL_S = 6;
const DEBOUNCE_WINDOW_URGENT_S = 2;

function debounceWindowFor(msg: MessageDTO): number {
  // Gateway treats messages containing "@" as urgent (shorter window).
  return (msg.body || "").includes("@")
    ? DEBOUNCE_WINDOW_URGENT_S
    : DEBOUNCE_WINDOW_NORMAL_S;
}

/**
 * Strip between TopicHeader and the chat stream. Surfaces what state the
 * agent is in:
 *   • idle — "Neo 在听 · 读到 40s 前 · 上次发言 7m 前"
 *   • thinking — "Neo 思考中 · 已 12s" (pulsing dot, brick-red accent)
 *   • impending — "Neo 即将介入 (X 秒后)" (briefly, after user sends + before agent posts status)
 */
export function AgentListenStatus({ messages, workspaceMembers = [], onJumpToUnread }: Props) {
  // Force a re-render every second so relative-time labels stay live in
  // the thinking/impending phases.
  const [, force] = useState(0);
  useEffect(() => {
    const t = setInterval(() => force((x) => x + 1), 1000);
    return () => clearInterval(t);
  }, []);

  const summary = useMemo(() => {
    let lastReadMsgId = 0;
    let lastReadAt: string | null = null;
    let lastAgentReplyAt: string | null = null;
    let lastAgentActivityAt: string | null = null;  // any agent post
    let lastAgentActivityId: number | null = null;
    let lastHumanMsg: MessageDTO | null = null;
    let pendingStatus: MessageDTO | null = null;
    let lastFailure: MessageDTO | null = null;

    for (const m of messages) {
      if (m.actor_type === "human") {
        if (!lastHumanMsg || m.created_at > lastHumanMsg.created_at) lastHumanMsg = m;
      } else if (m.actor_type === "agent") {
        if (!lastAgentActivityAt || m.created_at > lastAgentActivityAt) {
          lastAgentActivityAt = m.created_at;
          lastAgentActivityId = m.actor_id;
        }
        if (m.type === "chat") {
          if (!lastAgentReplyAt || m.created_at > lastAgentReplyAt) {
            lastAgentReplyAt = m.created_at;
          }
          const cites = (m.metadata as Record<string, unknown> | null)?.cites;
          if (Array.isArray(cites)) {
            const localMax = cites.reduce<number>(
              (a, c) => (typeof c === "number" && c > a ? c : a),
              0,
            );
            if (localMax > lastReadMsgId) {
              lastReadMsgId = localMax;
              lastReadAt = m.created_at;
            }
          }
        } else if (
          m.type === "finding" &&
          /(?:ERROR|调用失败|failed|failure)/i.test(m.body || "")
        ) {
          if (!lastFailure || m.created_at > lastFailure.created_at) {
            lastFailure = m;
          }
        }
      }
    }

    // Find latest agent status msg whose reply hasn't landed yet — that
    // means CC is still working.
    for (let i = messages.length - 1; i >= 0; i--) {
      const m = messages[i]!;
      if (m.actor_type !== "agent") continue;
      if (m.type === "status") {
        const meta = (m.metadata as Record<string, unknown> | null) ?? {};
        if (meta.phase === "thinking") {
          // Confirm no subsequent agent chat from same actor after this status.
          let answered = false;
          for (let j = i + 1; j < messages.length; j++) {
            const next = messages[j]!;
            if (
              next.actor_type === "agent" &&
              next.actor_id === m.actor_id &&
              (next.type === "chat" || next.type === "finding")
            ) {
              answered = true;
              break;
            }
          }
          if (!answered) {
            pendingStatus = m;
          }
        }
        break;  // only consider the latest status
      }
      // If we hit a chat first, the agent is past any status phase.
      if (m.type === "chat") break;
    }

    const unreadCount =
      lastReadMsgId === 0
        ? 0
        : messages.filter(
            (m) => m.id > lastReadMsgId && m.actor_type === "human",
          ).length;

    // Phase determination:
    // 1. thinking — pending status from agent without a reply yet
    // 2. impending — user posted recently AND no agent activity since
    // 3. idle — default
    let phase: "thinking" | "impending" | "failed" | "idle" = "idle";
    if (pendingStatus) {
      phase = "thinking";
    } else if (
      lastFailure &&
      (!lastAgentReplyAt || lastFailure.created_at >= lastAgentReplyAt)
    ) {
      phase = "failed";
    } else if (
      lastHumanMsg &&
      (!lastAgentActivityAt || lastHumanMsg.created_at > lastAgentActivityAt) &&
      secsSince(lastHumanMsg.created_at) < debounceWindowFor(lastHumanMsg) + 2
      // grace window: count down to fire moment + 2s buffer for SSE lag before
      // "思考中…" arrives; after that, fall back to "在听" idle.
    ) {
      phase = "impending";
    }

    const statusAgentId =
      pendingStatus?.actor_id ??
      lastFailure?.actor_id ??
      lastAgentActivityId ??
      workspaceMembers.find((m) => m.kind === "agent" && !m.deleted_at)?.id ??
      null;
    const statusAgent = workspaceMembers.find(
      (m) => m.kind === "agent" && m.id === statusAgentId,
    );

    return {
      lastReadAt, lastAgentReplyAt, unreadCount,
      agentLabel: statusAgent?.kind === "agent" ? agentShortName(statusAgent) : "agent",
      phase, pendingStatus, lastHumanMsg, lastFailure,
    };
  }, [messages, workspaceMembers]);

  // No data yet → don't show anything (avoids noisy header on a brand-new topic).
  if (
    !summary.lastReadAt &&
    !summary.lastAgentReplyAt &&
    summary.phase === "idle"
  ) return null;

  const handleJump = () => {
    if (onJumpToUnread) return onJumpToUnread();
    const el = document.querySelector<HTMLElement>("[data-unread]");
    el?.scrollIntoView({ behavior: "smooth", block: "center" });
  };

  // Visual style per phase. Thinking + impending both use accent (brick-red)
  // dot with halo + pulse animation so the human notices.
  const isWorking = summary.phase === "thinking" || summary.phase === "impending";
  const dotClass = isWorking
    ? "bg-accent shadow-[0_0_0_3px_color-mix(in_oklch,var(--color-accent)_30%,transparent)] animate-pulse"
    : summary.phase === "failed"
      ? "bg-finding shadow-[0_0_0_3px_color-mix(in_oklch,var(--color-finding)_25%,transparent)]"
    : "bg-status-on shadow-[0_0_0_3px_color-mix(in_oklch,var(--color-status-on)_25%,transparent)]";

  const labelClass =
    isWorking ? "text-accent-text" :
    summary.phase === "failed" ? "text-finding" :
    "text-text-muted";

  // Sits below the Composer — no rectangular frame, no border, transparent
  // background. The pulsing dot is the visual anchor. The label stays inline,
  // footnote-style, so it remains in peripheral view while the user types.
  return (
    <div
      data-testid="agent-listen-status"
      data-phase={summary.phase}
      className="px-3 md:px-6 pb-2 pt-0.5 text-[11px] italic text-text-dim flex items-center gap-1.5 select-none"
    >
      <span aria-hidden className={`w-[6px] h-[6px] rounded-full ${dotClass}`} />
      {summary.phase === "thinking" && summary.pendingStatus ? (
        <>
          <b className={`not-italic font-mono text-[10.5px] ${labelClass}`}>
            {summary.agentLabel} 思考中
          </b>
          <span className="not-italic font-mono text-text-dim">
            · 已 {Math.round(secsSince(summary.pendingStatus.created_at))}s
          </span>
        </>
      ) : summary.phase === "failed" && summary.lastFailure ? (
        <button
          type="button"
          onClick={() => {
            document
              .querySelector(`[data-msg-id="${summary.lastFailure!.id}"]`)
              ?.scrollIntoView({ behavior: "smooth", block: "center" });
          }}
          className={`not-italic font-mono text-[10.5px] ${labelClass} underline decoration-dotted hover:decoration-solid cursor-pointer`}
        >
          {summary.agentLabel} 调用失败 · 点击查看
        </button>
      ) : summary.phase === "impending" && summary.lastHumanMsg ? (
        <>
          <b className={`not-italic font-mono text-[10.5px] ${labelClass}`}>
            {summary.agentLabel} 即将介入
          </b>
          <span className="not-italic font-mono text-text-dim">
            · {Math.max(0, Math.ceil(
                debounceWindowFor(summary.lastHumanMsg)
                - secsSince(summary.lastHumanMsg.created_at)
              ))}s 后
          </span>
        </>
      ) : (
        <>
          <b className={`not-italic font-mono text-[10.5px] ${labelClass}`}>
            {summary.agentLabel} 在听
          </b>
          {summary.lastReadAt && <span>· 读到 {ago(summary.lastReadAt)}</span>}
          {summary.lastAgentReplyAt && <span>· 上次发言 {ago(summary.lastAgentReplyAt)}</span>}
        </>
      )}
      {summary.unreadCount > 0 && summary.phase === "idle" && (
        <button
          type="button"
          onClick={handleJump}
          className="ml-auto not-italic text-accent-text font-mono underline decoration-dotted hover:decoration-solid cursor-pointer"
        >
          ↑ {summary.unreadCount} 未读
        </button>
      )}
    </div>
  );
}
