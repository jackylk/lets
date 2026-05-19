import { useState } from "react";
import { useMyTokens, useCreateToken, useRevokeToken } from "../api/queries";
import { NewTokenDialog } from "./NewTokenDialog";

export function SettingsTokensPage() {
  const [openNew, setOpenNew] = useState(false);
  const tokens = useMyTokens();
  const createToken = useCreateToken();
  const revoke = useRevokeToken();

  return (
    <div className="flex flex-col gap-4 p-8 overflow-y-auto h-full">
      <div className="flex items-baseline justify-between">
        <h2 className="font-[var(--font-display)] text-2xl">Agent Tokens</h2>
        <button
          type="button"
          onClick={() => setOpenNew(true)}
          className="px-3 py-1.5 rounded bg-text text-bg text-[13px] font-medium"
        >+ New token</button>
      </div>

      <p className="text-[12px] text-text-muted max-w-2xl">
        每个本地 agent（Claude Code / Codex）通过一个 token 接入 Lets 后端。
        Token 只会在创建时显示一次，丢了只能 revoke + 新建。
      </p>

      {tokens.isLoading && <div className="text-text-dim">Loading…</div>}

      {tokens.data && tokens.data.length === 0 && (
        <div className="border border-dashed border-border rounded-lg p-6 text-center text-text-dim">
          No agent tokens yet. Click "+ New token" to issue one for your local CC or Codex.
        </div>
      )}

      {tokens.data && tokens.data.length > 0 && (
        <table className="w-full text-left text-[13px]">
          <thead>
            <tr className="text-text-dim text-[11px] uppercase tracking-wider">
              <th className="px-3 py-2">Label</th>
              <th className="px-3 py-2">Created</th>
              <th className="px-3 py-2">Last used</th>
              <th className="px-3 py-2">State</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {tokens.data.map((t) => (
              <tr key={t.id} className="border-t border-border-soft">
                <td className="px-3 py-2 font-mono">{t.label ?? `#${t.id}`}</td>
                <td className="px-3 py-2 text-text-muted">{t.created_at.slice(0, 16).replace("T", " ")}</td>
                <td className="px-3 py-2 text-text-muted">
                  {t.last_used_at ? t.last_used_at.slice(0, 16).replace("T", " ") : "never"}
                </td>
                <td className="px-3 py-2">
                  {t.revoked_at ? (
                    <span className="text-[11px] px-2 py-px rounded bg-finding-bg text-finding">revoked</span>
                  ) : (
                    <span className="text-[11px] px-2 py-px rounded bg-status-on/20 text-status-on">active</span>
                  )}
                </td>
                <td className="px-3 py-2 text-right">
                  {!t.revoked_at && (
                    <button
                      type="button"
                      onClick={() => revoke.mutate(t.id)}
                      disabled={revoke.isPending}
                      className="text-[12px] text-finding hover:underline disabled:opacity-50"
                    >Revoke</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {openNew && (
        <NewTokenDialog
          onCreate={(input) => createToken.mutateAsync(input)}
          onClose={() => setOpenNew(false)}
        />
      )}
    </div>
  );
}
