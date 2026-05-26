import { useEffect, useState, type FormEvent } from "react";
import {
  useMyTokens, useRevokeToken, useUpdateAgentModel,
  useSessionMe, useLogout, useUpdateMyName,
} from "../api/queries";
import { agentShortName, roleTitle } from "../agent/display";
import { ConnectAgentDialog } from "./ConnectAgentDialog";

interface Props {
  workspaceName?: string;
  workspaceSlug?: string;
}

export function SettingsTokensPage({ workspaceName, workspaceSlug }: Props = {}) {
  const [openNew, setOpenNew] = useState(false);
  const [draftName, setDraftName] = useState("");
  const [savedName, setSavedName] = useState<string | null>(null);
  const tokens = useMyTokens();
  const revoke = useRevokeToken();
  const updateModel = useUpdateAgentModel();
  const updateName = useUpdateMyName();
  const session = useSessionMe();
  const logout = useLogout();

  const human = session.data?.human;
  const normalizedDraftName = draftName.trim();

  useEffect(() => {
    if (human?.name) setDraftName(human.name);
  }, [human?.name]);

  function submitName(event: FormEvent) {
    event.preventDefault();
    if (!normalizedDraftName || normalizedDraftName === human?.name) return;
    setSavedName(null);
    updateName.mutate(normalizedDraftName, {
      onSuccess: (res) => setSavedName(res.human.name),
    });
  }

  return (
    <div className="flex flex-col gap-6 p-8 overflow-y-auto h-full">
      <section className="flex items-center justify-between border-b border-border-soft pb-4">
        <div className="flex flex-col gap-0.5">
          <h2 className="font-[var(--font-display)] text-2xl">账户</h2>
          {human ? (
            <form onSubmit={submitName} className="mt-2 flex flex-col gap-2">
              <div className="flex flex-wrap items-end gap-2">
                <label className="flex flex-col gap-1 text-[12px] text-text-dim">
                  名字
                  <input
                    value={draftName}
                    onChange={(event) => {
                      setDraftName(event.target.value);
                      setSavedName(null);
                    }}
                    maxLength={40}
                    className="w-56 max-w-full rounded border border-border bg-bg px-2.5 py-1.5 text-[13px] text-text outline-none focus:border-text"
                  />
                </label>
                <button
                  type="submit"
                  disabled={
                    updateName.isPending ||
                    !normalizedDraftName ||
                    normalizedDraftName === human.name
                  }
                  className="px-3 py-1.5 rounded border border-border text-[13px] text-text hover:bg-hover disabled:opacity-50"
                >
                  {updateName.isPending ? "保存中…" : "保存"}
                </button>
              </div>
              {human.github_login && (
                <span className="text-[13px] text-text-dim">@{human.github_login}</span>
              )}
              {savedName && (
                <span className="text-[12px] text-text-dim">
                  已保存为 {savedName}
                </span>
              )}
              {updateName.isError && (
                <span className="text-[12px] text-red-500">保存失败，请稍后再试</span>
              )}
            </form>
          ) : (
            <div className="text-[13px] text-text-dim">未登录</div>
          )}
        </div>
        <button
          type="button"
          onClick={() => logout.mutate()}
          disabled={logout.isPending}
          className="px-3 py-1.5 rounded border border-border text-[13px] text-text hover:bg-hover disabled:opacity-50"
        >
          {logout.isPending ? "退出中…" : "退出登录"}
        </button>
      </section>

      <div className="flex items-baseline justify-between">
        <h2 className="font-[var(--font-display)] text-2xl">我的电脑和 Agent</h2>
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
              <th className="px-3 py-2">模型</th>
              <th className="px-3 py-2">添加时间</th>
              <th className="px-3 py-2">最近连接</th>
              <th className="px-3 py-2">状态</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {tokens.data.map((t) => (
              <tr key={t.id} className="border-t border-border-soft">
                <td className="px-3 py-2">
                  {t.agent_instance ? (
                    <div className="flex flex-col leading-tight">
                      <span>{agentShortName(t.agent_instance)}</span>
                      <span className="text-[11px] text-text-dim">
                        {roleTitle(t.agent_instance.role)}
                      </span>
                    </div>
                  ) : (
                    <span>Agent</span>
                  )}
                </td>
                <td className="px-3 py-2 font-mono">
                  {t.agent_instance?.device_label ?? t.label ?? `#${t.id}`}
                </td>
                <td className="px-3 py-2">
                  {t.agent_instance?.role === "claude" && t.agent_instance?.id ? (
                    <select
                      aria-label={`${t.agent_instance.device_label} 模型`}
                      value={t.agent_instance.model ?? "claude-opus-4-7"}
                      disabled={updateModel.isPending}
                      onChange={(e) =>
                        updateModel.mutate({
                          agentInstanceId: t.agent_instance!.id,
                          model: e.target.value,
                        })
                      }
                      className="border border-border rounded px-2 py-1 bg-surface-elev text-[12px]"
                    >
                      <option value="haiku">Haiku</option>
                      <option value="sonnet">Sonnet</option>
                      <option value="sonnet-4.6">Sonnet 4.6</option>
                      <option value="claude-opus-4-7">Opus</option>
                    </select>
                  ) : (
                    <span className="text-text-dim">-</span>
                  )}
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

      {openNew && (
        <ConnectAgentDialog
          workspaceName={workspaceName}
          workspaceSlug={workspaceSlug}
          onClose={() => setOpenNew(false)}
        />
      )}
    </div>
  );
}
