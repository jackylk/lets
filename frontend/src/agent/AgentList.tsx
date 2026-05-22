import { useMyAgents } from "../api/queries";

interface Props {
  onSelectAgent?: (agentId: number) => void;
}

export function AgentList({ onSelectAgent }: Props) {
  const agents = useMyAgents();

  if (agents.isLoading) return <div className="p-6 text-text-dim">加载中...</div>;
  if (agents.isError) return <div className="p-6 text-text-dim">加载失败</div>;

  return (
    <div className="mx-auto max-w-2xl p-6">
      <h1 className="mb-6 text-xl font-semibold">我的 Agents</h1>
      <div className="divide-y divide-border-soft border-y border-border-soft">
        {(agents.data ?? []).map((agent) => (
          <button
            key={agent.agent_instance_id}
            type="button"
            onClick={() => onSelectAgent?.(agent.agent_instance_id)}
            className="flex w-full items-center justify-between py-4 text-left hover:bg-surface-hover"
          >
            <div>
              <div className="text-sm text-text">
                {agent.display_name || `${agent.role}-${agent.agent_instance_id}`}
              </div>
              <div className="text-xs text-text-dim">{agent.device_label}</div>
            </div>
            <div className="text-xs text-text-dim">
              {agent.deleted_at ? "已退役" : agent.paused_at ? "已暂停" : "可用"}
            </div>
          </button>
        ))}
        {(agents.data ?? []).length === 0 && (
          <div className="py-8 text-sm text-text-dim">暂无注册的 Agent。</div>
        )}
      </div>
    </div>
  );
}
