import { useState } from "react";
import { useMyTokens, useRevokeToken } from "../api/queries";
import { ConnectAgentDialog } from "./ConnectAgentDialog";

export function SettingsTokensPage() {
  const [openNew, setOpenNew] = useState(false);
  const tokens = useMyTokens();
  const revoke = useRevokeToken();

  const agentName = (role?: string | null) => {
    if (role === "claude") return "Claude Code";
    if (role === "codex") return "Codex";
    return role ?? "Agent";
  };

  return (
    <div className="flex flex-col gap-4 p-8 overflow-y-auto h-full">
      <div className="flex items-baseline justify-between">
        <h2 className="font-[var(--font-display)] text-2xl">电脑和 Agent</h2>
        <button
          type="button"
          onClick={() => setOpenNew(true)}
          className="px-3 py-1.5 rounded bg-text text-bg text-[13px] font-medium"
        >+ 添加</button>
      </div>

      <p className="text-[12px] text-text-muted max-w-2xl">
        每台电脑上的 Claude Code / Codex 都是一个独立条目。在哪台电脑上跑过 <code className="font-mono">lets add</code>，它就会出现在这里——网站本身不直接装 agent。
      </p>

      {tokens.isLoading && <div className="text-text-dim">Loading…</div>}

      {tokens.data && tokens.data.length === 0 && (
        <div className="border border-dashed border-border rounded-lg p-6 text-center text-text-dim">
          还没有接入任何电脑。点击「+ 添加」拿到接入命令。
        </div>
      )}

      {tokens.data && tokens.data.length > 0 && (
        <table className="w-full text-left text-[13px]">
          <thead>
            <tr className="text-text-dim text-[11px] uppercase tracking-wider">
              <th className="px-3 py-2">Agent</th>
              <th className="px-3 py-2">电脑</th>
              <th className="px-3 py-2">添加时间</th>
              <th className="px-3 py-2">最近连接</th>
              <th className="px-3 py-2">状态</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {tokens.data.map((t) => (
              <tr key={t.id} className="border-t border-border-soft">
                <td className="px-3 py-2">{agentName(t.agent_instance?.role)}</td>
                <td className="px-3 py-2 font-mono">
                  {t.agent_instance?.device_label ?? t.label ?? `#${t.id}`}
                </td>
                <td className="px-3 py-2 text-text-muted">{t.created_at.slice(0, 16).replace("T", " ")}</td>
                <td className="px-3 py-2 text-text-muted">
                  {t.last_used_at ? t.last_used_at.slice(0, 16).replace("T", " ") : "尚未连接"}
                </td>
                <td className="px-3 py-2">
                  {t.revoked_at ? (
                    <span className="text-[11px] px-2 py-px rounded bg-finding-bg text-finding">已移除</span>
                  ) : (
                    <span className="text-[11px] px-2 py-px rounded bg-status-on/20 text-status-on">可连接</span>
                  )}
                </td>
                <td className="px-3 py-2 text-right">
                  {!t.revoked_at && (
                    <button
                      type="button"
                      onClick={() => revoke.mutate(t.id)}
                      disabled={revoke.isPending}
                      className="text-[12px] text-finding hover:underline disabled:opacity-50"
                    >移除</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {openNew && <ConnectAgentDialog onClose={() => setOpenNew(false)} />}
    </div>
  );
}
