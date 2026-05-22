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

export function InviteAgentDialog({ workspaceName, workspaceSlug, onClose }: Props) {
  const [role, setRole] = useState<RoleId>("claude");
  const [copied, setCopied] = useState(false);

  const command = `lets add ${role} --workspace ${workspaceSlug}`;

  const onCopy = async () => {
    await navigator.clipboard.writeText(command);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="fixed inset-0 bg-black/40 grid place-items-center z-50">
      <div className="bg-bg border border-border rounded p-6 max-w-md w-full">
        <h2 className="text-lg font-[var(--font-display)] mb-3">
          邀请 agent 加入「{workspaceName}」
        </h2>
        <p className="text-sm text-text-dim mb-3">
          选一个 agent，然后在你电脑的终端跑这条命令。agent 会用你的身份加入这个工作区。
        </p>

        <div
          role="radiogroup"
          aria-label="Agent role"
          className="flex gap-2 mb-3"
        >
          {ROLES.map((r) => (
            <button
              key={r.id}
              type="button"
              role="radio"
              aria-checked={role === r.id}
              onClick={() => setRole(r.id)}
              className={
                "text-xs px-3 py-1.5 border rounded transition-colors " +
                (role === r.id
                  ? "border-accent text-text bg-surface-elev"
                  : "border-border text-text-dim hover:text-text")
              }
            >
              {r.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2 mb-4">
          <code
            data-testid="invite-agent-command"
            className="flex-1 bg-hover px-3 py-2 rounded text-xs break-all font-mono"
          >
            {command}
          </code>
          <button
            type="button"
            onClick={onCopy}
            className="text-xs px-3 py-2 border border-border rounded hover:bg-hover"
          >
            {copied ? "已复制" : "复制"}
          </button>
        </div>

        <p className="text-xs text-text-dim mb-4">
          没装过 lets？先看 README 装一下，然后再跑这条命令。
        </p>

        <div className="flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="text-sm px-4 py-2 border border-border rounded hover:bg-hover"
          >
            完成
          </button>
        </div>
      </div>
    </div>
  );
}
