import { useMyAgents } from "../api/queries";
import { agentShortName, agentStatusLabel } from "./display";

interface Props {
  onSelectAgent?: (agentId: number) => void;
}

export function AgentList({ onSelectAgent }: Props) {
  const agents = useMyAgents();

  if (agents.isLoading) return <div className="p-6 text-text-dim">加载中...</div>;
  if (agents.isError) return <div className="p-6 text-text-dim">加载失败</div>;

  return (
    <div className="mx-auto max-w-3xl p-6">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-text">我的 Agents</h1>
        <p className="mt-1 text-sm text-text-dim">
          这里管理你拥有的 agent。本页是全局状态；它们加入哪些 workspace 在下方列出。
        </p>
      </div>
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
                {agentShortName(agent)}
              </div>
              <div className="text-xs text-text-dim">
                {agent.role} · {agent.device_label || "unknown device"}
              </div>
              <div className="mt-1 text-xs text-text-dim">
                {(agent.workspaces ?? []).length === 0
                  ? "尚未加入 workspace"
                  : `已加入 ${(agent.workspaces ?? []).map((w) => w.name).join("、")}`}
              </div>
            </div>
            <div className="text-xs text-text-dim">
              {agentStatusLabel(agent)}
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
