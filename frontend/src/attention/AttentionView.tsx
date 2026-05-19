import { useTopicMessages } from "../api/queries";
import type { MessageDTO } from "../api/types";
import { AttentionGroup } from "./AttentionGroup";
import { AttentionCard } from "./AttentionCard";

interface Props { userName: string }

function avatarFor(m: MessageDTO): { kind: "human" | "claude" | "codex" | "system"; initial: string; label: string } {
  if (m.actor_type === "human") {
    const n = String(m.actor_id ?? "?");
    return { kind: "human", initial: n[0]?.toUpperCase() ?? "?", label: `human#${n}` };
  }
  if (m.actor_type === "agent") {
    return { kind: "claude", initial: "CC", label: `agent#${m.actor_id}` };
  }
  return { kind: "system", initial: "S", label: "system" };
}

export function AttentionView({ userName }: Props) {
  const { data, isLoading } = useTopicMessages(1);
  const messages = data?.messages ?? [];

  const decide = messages.filter((m) => m.type === "spec_change" || (m.type === "chat" && m.body.endsWith("？")));
  const proactive = messages.filter((m) => m.type === "proactive_finding");
  const peer = messages.filter((m) => m.type === "question");

  return (
    <div className="flex flex-col gap-6 px-8 py-6 overflow-y-auto h-full">
      <div>
        <h2 className="font-[var(--font-display)] text-2xl">早上好，{userName}。</h2>
        <p className="text-text-muted text-[14px] mt-1">
          过去一夜，团队已经有 {decide.length + proactive.length + peer.length} 件事在你的清单里。
        </p>
      </div>
      {isLoading && <div className="text-text-dim">加载中…</div>}

      <AttentionGroup heading="需要决定" count={decide.length}>
        {decide.map((m) => {
          const a = avatarFor(m);
          return (
            <AttentionCard
              key={m.id}
              avatar={{ kind: a.kind, initial: a.initial }}
              whoLabel={a.label}
              timeIso={m.created_at}
              what={m.body}
              topicRef={{ id: "T-PPT", title: "为 Agent 记忆写一个研讨 PPT" }}
              primary={{ label: m.type === "spec_change" ? "Approve" : "采纳", onClick: () => {} }}
              secondary={{ label: m.type === "spec_change" ? "看 diff" : "先不", onClick: () => {} }}
            />
          );
        })}
      </AttentionGroup>

      <AttentionGroup heading="Agent 主动发现" count={proactive.length}>
        {proactive.map((m) => {
          const a = avatarFor(m);
          return (
            <AttentionCard
              key={m.id}
              avatar={{ kind: a.kind, initial: a.initial }}
              whoLabel={a.label}
              timeIso={m.created_at}
              what={m.body}
              topicRef={{ id: "T-PPT", title: "为 Agent 记忆写一个研讨 PPT" }}
              primary={{ label: "采纳建议", onClick: () => {} }}
              secondary={{ label: "略过", onClick: () => {} }}
            />
          );
        })}
      </AttentionGroup>

      <AttentionGroup heading="同事消息" count={peer.length}>
        {peer.map((m) => {
          const a = avatarFor(m);
          return (
            <AttentionCard
              key={m.id}
              avatar={{ kind: a.kind, initial: a.initial }}
              whoLabel={a.label}
              timeIso={m.created_at}
              what={m.body}
              topicRef={{ id: "DM", title: "private message" }}
              primary={{ label: "继续聊", onClick: () => {} }}
              secondary={{ label: "@claude 跟进", onClick: () => {} }}
            />
          );
        })}
      </AttentionGroup>
    </div>
  );
}
