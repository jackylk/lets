import { useState } from "react";

interface Props {
  workspaceName: string;
  workspaceSlug: string;
  onClose: () => void;
}

const ROLES = [
  { id: "claude", label: "Claude Code" },
  { id: "codex", label: "Codex CLI" },
] as const;

type RoleId = (typeof ROLES)[number]["id"];

function installCommand() {
  const origin =
    typeof window !== "undefined" ? window.location.origin : "https://lets.up.railway.app";
  return `curl -fsSL ${origin}/install | bash`;
}

async function copyText(value: string) {
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(value);
      return true;
    } catch {
      // Fall through to the selection-based fallback below.
    }
  }

  const textarea = document.createElement("textarea");
  textarea.value = value;
  textarea.setAttribute("readonly", "true");
  textarea.style.position = "fixed";
  textarea.style.left = "-9999px";
  document.body.appendChild(textarea);
  textarea.select();
  try {
    return document.execCommand?.("copy") === true;
  } finally {
    document.body.removeChild(textarea);
  }
}

export function InviteAgentDialog({ workspaceName, workspaceSlug, onClose }: Props) {
  const [role, setRole] = useState<RoleId>("claude");
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const install = installCommand();
  const command = `lets add ${role} --workspace ${workspaceSlug}`;

  const onCopy = async (key: string, value: string) => {
    const ok = await copyText(value);
    if (!ok) return;
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 1500);
  };

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/40 px-4">
      <div className="w-full max-w-md rounded border border-border bg-bg p-6 shadow-[0_18px_56px_rgba(44,42,38,0.18)]">
        <h2 className="mb-3 font-[var(--font-display)] text-lg text-text">
          邀请 agent 加入「{workspaceName}」
        </h2>
        <p className="mb-4 text-sm leading-6 text-text-dim">
          在要运行 agent 的电脑终端里执行下面命令。agent 会用你的身份加入这个工作区。
        </p>

        <div
          role="radiogroup"
          aria-label="Agent role"
          className="mb-4 flex gap-2"
        >
          {ROLES.map((r) => (
            <button
              key={r.id}
              type="button"
              role="radio"
              aria-checked={role === r.id}
              onClick={() => setRole(r.id)}
              className={
                "rounded border px-3 py-1.5 text-xs transition-colors " +
                (role === r.id
                  ? "border-accent text-text bg-surface-elev"
                  : "border-border text-text-dim hover:text-text")
              }
            >
              {r.label}
            </button>
          ))}
        </div>

        <div className="mb-4 flex flex-col gap-3">
          <CommandRow
            label="1. 安装 lets"
            testId="invite-agent-install-command"
            command={install}
            copied={copiedKey === "install"}
            onCopy={() => onCopy("install", install)}
          />
          <CommandRow
            label="2. 添加 agent"
            testId="invite-agent-command"
            command={command}
            copied={copiedKey === "add"}
            onCopy={() => onCopy("add", command)}
          />
        </div>

        <p className="mb-4 text-xs leading-5 text-text-dim">
          已经装过 lets 的电脑可以直接跳到第 2 步。
        </p>

        <div className="flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="rounded bg-text px-3 py-1.5 text-[13px] font-medium text-bg hover:opacity-90"
          >
            完成
          </button>
        </div>
      </div>
    </div>
  );
}

function CommandRow({
  label,
  testId,
  command,
  copied,
  onCopy,
}: {
  label: string;
  testId: string;
  command: string;
  copied: boolean;
  onCopy: () => void;
}) {
  return (
    <div>
      <div className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-text-dim">
        {label}
      </div>
      <div className="rounded border border-border bg-surface-elev p-2.5">
        <div className="flex items-center gap-2">
          <code
            data-testid={testId}
            className="min-w-0 flex-1 overflow-x-auto whitespace-nowrap font-mono text-[13px] text-text"
          >
            {command}
          </code>
          <button
            type="button"
            onClick={onCopy}
            className="shrink-0 rounded bg-text px-2.5 py-1 text-[12px] font-medium text-bg hover:opacity-90"
          >
            {copied ? "已复制" : "复制"}
          </button>
        </div>
      </div>
    </div>
  );
}
