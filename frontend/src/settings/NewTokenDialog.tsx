import { useState } from "react";
import type { CreateTokenResponseDTO } from "../api/types";

interface Props {
  onCreate: (input: { label: string; role: string; device_label: string }) => Promise<CreateTokenResponseDTO>;
  onClose: () => void;
}

type Stage =
  | { kind: "form" }
  | { kind: "submitting" }
  | { kind: "reveal"; token: CreateTokenResponseDTO }
  | { kind: "error"; message: string };

export function NewTokenDialog({ onCreate, onClose }: Props) {
  const [stage, setStage] = useState<Stage>({ kind: "form" });
  const [role, setRole] = useState("claude");
  const [device, setDevice] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!device.trim()) return;
    setStage({ kind: "submitting" });
    try {
      const label = `${role} on ${device.trim()}`;
      const t = await onCreate({ label, role, device_label: device.trim() });
      setStage({ kind: "reveal", token: t });
    } catch (err) {
      setStage({ kind: "error", message: err instanceof Error ? err.message : String(err) });
    }
  }

  return (
    <div className="fixed inset-0 bg-black/30 grid place-items-center z-50">
      <div className="bg-bg border border-border rounded-xl w-full max-w-md p-5">
        {stage.kind !== "reveal" ? (
          <form onSubmit={submit} className="flex flex-col gap-3">
            <h2 className="font-[var(--font-display)] text-lg">添加电脑和 Agent</h2>
            <p className="text-[12px] text-text-muted">
              选择这台电脑上要接入 Lets 的本地 Agent。创建后会生成一段连接密钥，只显示一次。
            </p>
            <label className="text-[12px] text-text-muted flex flex-col gap-1">
              Agent
              <select
                value={role} onChange={(e) => setRole(e.target.value)}
                className="border border-border rounded px-2 py-1.5 bg-surface-elev"
              >
                <option value="claude">Claude Code</option>
                <option value="codex">Codex</option>
              </select>
            </label>
            <label className="text-[12px] text-text-muted flex flex-col gap-1">
              电脑名称
              <input
                value={device} onChange={(e) => setDevice(e.target.value)}
                placeholder="jacky-mbp"
                className="border border-border rounded px-2 py-1.5 bg-surface-elev"
              />
            </label>
            {stage.kind === "error" && (
              <div className="text-[12px] text-finding">{stage.message}</div>
            )}
            <div className="flex gap-2 mt-1">
              <button
                type="button" onClick={onClose}
                className="px-3 py-1.5 rounded border border-border text-[13px]"
              >取消</button>
              <div className="flex-1" />
              <button
                type="submit"
                disabled={stage.kind === "submitting"}
                className="px-3 py-1.5 rounded bg-text text-bg text-[13px] font-medium disabled:opacity-50"
              >添加</button>
            </div>
          </form>
        ) : (
          <div className="flex flex-col gap-3">
            <h2 className="font-[var(--font-display)] text-lg">复制连接密钥</h2>
            <p className="text-[12px] text-text-muted">
              这段密钥只显示一次。把它填到本机 {stage.token.agent_instance.role === "claude" ? "Claude Code" : "Codex"} 的 MCP 配置里。
            </p>
            <pre className="bg-surface border border-border rounded p-2.5 font-mono text-[12px] break-all">
              {stage.token.value}
            </pre>
            <div className="text-[11px] text-text-dim">
              已添加 <code className="font-mono">
                {stage.token.agent_instance.role === "claude" ? "Claude Code" : "Codex"} · {stage.token.agent_instance.device_label}
              </code>
            </div>
            <div className="flex justify-end mt-1">
              <button
                type="button" onClick={onClose}
                className="px-3 py-1.5 rounded bg-text text-bg text-[13px] font-medium"
              >完成</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
