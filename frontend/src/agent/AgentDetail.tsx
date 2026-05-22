import { useEffect, useState } from "react";
import {
  useAgentDetail,
  useDeleteAgent,
  usePauseAgent,
  useResumeAgent,
  useUpdateAgentDisplayName,
} from "../api/queries";
import { agentShortName, agentStatusLabel, roleTitle } from "./display";

interface Props {
  agentId: number;
  onBack: () => void;
}

function formatNumber(value: number | string | null | undefined) {
  return Number(value ?? 0).toLocaleString();
}

export function AgentDetail({ agentId, onBack }: Props) {
  const detail = useAgentDetail(agentId);
  const pause = usePauseAgent();
  const resume = useResumeAgent();
  const revoke = useDeleteAgent();
  const rename = useUpdateAgentDisplayName();
  const [draftName, setDraftName] = useState("");

  useEffect(() => {
    if (detail.data) setDraftName(agentShortName(detail.data));
  }, [detail.data]);

  if (detail.isLoading) return <div className="p-6 text-text-dim">加载中...</div>;
  if (detail.isError || !detail.data) {
    return <div className="p-6 text-text-dim">Agent 不存在或无法加载</div>;
  }

  const agent = detail.data;
  const paused = Boolean(agent.paused_at);
  const retired = Boolean(agent.deleted_at);
  const status = agentStatusLabel(agent);

  return (
    <div className="h-full overflow-auto bg-bg">
      <div className="mx-auto max-w-3xl px-8 py-7">
        <button
          type="button"
          onClick={onBack}
          className="mb-6 text-xs text-text-dim hover:text-text"
        >
          返回
        </button>

        <div className="mb-7 flex items-start justify-between gap-6">
          <div>
            <h1 className="text-2xl font-semibold text-text">{agentShortName(agent)}</h1>
            <div className="mt-1 text-sm text-text-dim">
              {roleTitle(agent.role)} · 由 {agent.human_name} 管理 · {status}
            </div>
          </div>
          <div className="flex gap-2">
            {!retired && (
              paused ? (
                <button
                  type="button"
                  onClick={() => resume.mutate(agentId)}
                  className="rounded border border-border px-3 py-1.5 text-sm hover:bg-surface-hover"
                >
                  恢复
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => pause.mutate(agentId)}
                  className="rounded border border-border px-3 py-1.5 text-sm hover:bg-surface-hover"
                >
                  暂停
                </button>
              )
            )}
            {!retired && (
              <button
                type="button"
                onClick={() => {
                  if (window.confirm("撤销后此 agent 需要重新 lets add 才能回来。")) {
                    revoke.mutate(agentId);
                  }
                }}
                className="rounded border border-border px-3 py-1.5 text-sm text-danger hover:bg-surface-hover"
              >
                撤销
              </button>
            )}
          </div>
        </div>

        <section className="mb-8">
          <h2 className="mb-3 text-xs font-semibold uppercase text-text-dim">基本信息</h2>
          <form
            className="mb-5 flex max-w-md items-end gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              const next = draftName.trim();
              if (!next || next === agentShortName(agent)) return;
              rename.mutate({ agentInstanceId: agentId, displayName: next });
            }}
          >
            <label className="min-w-0 flex-1">
              <span className="block text-xs text-text-dim">展示名</span>
              <input
                value={draftName}
                onChange={(e) => setDraftName(e.target.value)}
                maxLength={40}
                className="mt-1 w-full rounded border border-border bg-surface-elev px-2 py-1.5 text-sm text-text"
              />
            </label>
            <button
              type="submit"
              disabled={rename.isPending || !draftName.trim() || draftName.trim() === agentShortName(agent)}
              className="rounded border border-border px-3 py-1.5 text-sm hover:bg-surface-hover disabled:opacity-50"
            >
              保存
            </button>
          </form>
          <div className="grid grid-cols-2 gap-x-8 gap-y-3 text-sm">
            <Info label="Type" value={roleTitle(agent.role)} />
            <Info label="Model" value={agent.model || "-"} />
            <Info label="Device" value={agent.device_label || "-"} />
            <Info label="Last activity" value={agent.last_seen_at || "-"} />
          </div>
        </section>

        <section className="mb-8">
          <h2 className="mb-3 text-xs font-semibold uppercase text-text-dim">加入的 workspace</h2>
          <div className="divide-y divide-border-soft border-y border-border-soft">
            {agent.workspaces.length === 0 ? (
              <div className="py-3 text-sm text-text-dim">尚未加入任何 workspace</div>
            ) : (
              agent.workspaces.map((workspace) => (
                <div key={workspace.id} className="flex items-center justify-between py-3 text-sm">
                  <div>
                    <div className="text-text">{workspace.name}</div>
                    <div className="text-xs text-text-dim">{workspace.slug}</div>
                  </div>
                  <div className="text-xs text-text-dim">{workspace.joined_at}</div>
                </div>
              ))
            )}
          </div>
        </section>

        <section className="mb-8">
          <h2 className="mb-3 text-xs font-semibold uppercase text-text-dim">活动统计</h2>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <Metric label="参与话题" value={formatNumber(agent.stats.topic_count)} />
            <Metric label="发送消息" value={formatNumber(agent.stats.message_count)} />
            <Metric label="输入 token" value={formatNumber(agent.stats.input_tokens)} />
            <Metric label="输出 token" value={formatNumber(agent.stats.output_tokens)} />
          </div>
          <div className="mt-2 text-xs text-text-dim">
            Usage stats from {agent.usage_started_at}
          </div>
        </section>

        {agent.quota && (
          <section className="mb-8">
            <h2 className="mb-3 text-xs font-semibold uppercase text-text-dim">Plan usage</h2>
            <div className="text-sm text-text-dim">配额数据由本地 gateway 上报。</div>
          </section>
        )}

        <section>
          <h2 className="mb-3 text-xs font-semibold uppercase text-text-dim">最近活跃话题</h2>
          <div className="divide-y divide-border-soft border-y border-border-soft">
            {agent.recent_topics.length === 0 ? (
              <div className="py-3 text-sm text-text-dim">暂无消息</div>
            ) : (
              agent.recent_topics.map((topic) => (
                <div key={topic.id} className="flex items-center justify-between py-3 text-sm">
                  <div>
                    <div className="text-text">{topic.title}</div>
                    <div className="text-xs text-text-dim">{topic.slug}</div>
                  </div>
                  <div className="text-xs text-text-dim">
                    {formatNumber(topic.message_count)} 条
                  </div>
                </div>
              ))
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs text-text-dim">{label}</div>
      <div className="mt-0.5 text-text">{value}</div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="border-y border-border-soft py-3">
      <div className="text-lg font-semibold text-text">{value}</div>
      <div className="mt-1 text-xs text-text-dim">{label}</div>
    </div>
  );
}
