import { useState } from "react";

type Role = "claude" | "codex";

interface Props {
  onClose: () => void;
}

function useCopy() {
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const copy = async (key: string, text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedKey(key);
      setTimeout(() => setCopiedKey((c) => (c === key ? null : c)), 1500);
    } catch {
      /* ignore */
    }
  };
  return { copiedKey, copy };
}

/**
 * "Add a computer / agent" — but the actual binding has to happen on the
 * target machine (Railway-hosted backend can't reach a user's laptop). So
 * this dialog is purely instructional: show the exact terminal command for
 * the role they want. The agent list below auto-refreshes once the local
 * `lets add` finishes its device-flow handshake.
 */
export function ConnectAgentDialog({ onClose }: Props) {
  const [role, setRole] = useState<Role>("claude");
  const origin =
    typeof window !== "undefined" ? window.location.origin : "https://lets.up.railway.app";
  const { copiedKey, copy } = useCopy();

  const installCmd =
    role === "claude"
      ? `curl -fsSL ${origin}/install | bash`
      : `curl -fsSL ${origin}/install | LETS_AGENT_ROLE=codex bash`;
  const letsAddCmd = `lets add ${role}`;

  return (
    <div className="fixed inset-0 bg-black/30 grid place-items-center z-50 p-4">
      <div className="bg-bg border border-border rounded-xl w-full max-w-xl p-5 flex flex-col gap-4 shadow-lg">
        <header className="flex items-baseline justify-between gap-3">
          <h2 className="font-[var(--font-display)] text-xl">添加 Agent</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="关闭"
            className="text-text-dim hover:text-text text-[14px]"
          >
            ✕
          </button>
        </header>

        <p className="text-[12.5px] text-text-muted leading-relaxed">
          在你想接入的那台电脑的终端里跑下面的命令。授权后这台 agent 会自动出现在下面的列表里——网站这边不用再做别的。
        </p>

        <div className="flex gap-2 items-center text-[12.5px]">
          <span className="text-text-muted">要装哪种 agent？</span>
          <select
            value={role}
            onChange={(e) => setRole(e.target.value as Role)}
            className="border border-border rounded px-2 py-1 bg-surface-elev text-[13px]"
          >
            <option value="claude">Claude Code</option>
            <option value="codex">Codex</option>
          </select>
        </div>

        <section className="flex flex-col gap-2">
          <div className="text-[12px] uppercase tracking-wider text-text-dim">
            第一次在这台电脑上装 Lets
          </div>
          <CommandRow
            id="install"
            command={installCmd}
            copiedKey={copiedKey}
            onCopy={copy}
          />
        </section>

        <section className="flex flex-col gap-2">
          <div className="text-[12px] uppercase tracking-wider text-text-dim">
            已经装过 lets（加另一个 agent）
          </div>
          <CommandRow
            id="lets-add"
            command={letsAddCmd}
            copiedKey={copiedKey}
            onCopy={copy}
          />
        </section>

        <p className="text-[11.5px] text-text-dim italic leading-relaxed">
          会弹浏览器让你授权这台电脑，授权完成后 gateway 就在后台跑起来了。下次重启电脑也会自动起。
        </p>

        <div className="flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-1.5 rounded bg-text text-bg text-[13px] font-medium"
          >
            知道了
          </button>
        </div>
      </div>
    </div>
  );
}

function CommandRow({
  id,
  command,
  copiedKey,
  onCopy,
}: {
  id: string;
  command: string;
  copiedKey: string | null;
  onCopy: (key: string, text: string) => void;
}) {
  return (
    <div className="bg-surface-elev border border-border rounded flex items-center gap-2 px-3 py-2">
      <code className="font-mono text-[13px] text-text flex-1 min-w-0 overflow-x-auto whitespace-nowrap">
        {command}
      </code>
      <button
        type="button"
        onClick={() => onCopy(id, command)}
        className="shrink-0 px-2.5 py-1 rounded text-[12px] font-medium bg-text text-bg hover:opacity-90"
      >
        {copiedKey === id ? "已复制" : "复制"}
      </button>
    </div>
  );
}
