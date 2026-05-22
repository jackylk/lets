import { useState } from "react";

function useInstallCommand() {
  const origin =
    typeof window !== "undefined" ? window.location.origin : "https://lets.up.railway.app";
  return `curl -fsSL ${origin}/install | bash`;
}

function useCopy(command: string) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(command);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  };
  return { copied, copy };
}

/**
 * Greets a freshly-logged-in human who hasn't connected any computer yet.
 * Shows the one-line install command they should paste into a terminal —
 * derived from the current origin so it always points at the right backend.
 */
export function ConnectComputerCard() {
  const command = useInstallCommand();
  const { copied, copy } = useCopy(command);

  return (
    <div className="h-full w-full flex items-center justify-center p-6">
      <div className="max-w-2xl w-full flex flex-col items-center text-center gap-6">
        <div className="flex flex-col gap-3">
          <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight text-text">
            把这台电脑接上 Let's
          </h1>
          <p className="text-text-muted text-[15px] max-w-md mx-auto leading-relaxed">
            在终端里粘贴下面这条命令 + 回车。装好后默认浏览器会自动弹出来让你授权这台电脑，授权完就能在这里和你的 agent 聊天了。
          </p>
        </div>

        <div className="w-full bg-surface-elev border border-border rounded-lg shadow-sm">
          <div className="flex items-center justify-between gap-3 px-4 py-3.5">
            <code className="font-mono text-[13.5px] text-text whitespace-nowrap overflow-x-auto flex-1 text-left">
              {command}
            </code>
            <button
              type="button"
              onClick={copy}
              className="shrink-0 px-3 py-1.5 rounded text-[12.5px] font-medium bg-text text-bg hover:opacity-90 transition"
            >
              {copied ? "已复制" : "复制"}
            </button>
          </div>
        </div>

        <div className="text-[12.5px] text-text-dim space-y-1.5 max-w-md">
          <p>
            一条命令做完三件事：拉 gateway → 写 <span className="font-mono">~/.lets</span> → 弹浏览器让你授权这台电脑。
          </p>
          <p>
            授权完成后这页会自动出现你的 agent。需要多台电脑？在每台上跑同一条命令即可。
          </p>
        </div>
      </div>
    </div>
  );
}

const BANNER_DISMISS_KEY = "lets:connect-banner-dismissed";

/**
 * One-shot first-login hint: shows the install command once. After the user
 * dismisses it (or after they connect their first computer) it stays hidden.
 * The persistent re-add path lives in Settings → 电脑和 Agent.
 */
export function ConnectComputerBanner({ onDismiss }: { onDismiss?: () => void }) {
  const command = useInstallCommand();
  const { copied, copy } = useCopy(command);

  const dismiss = () => {
    try {
      window.localStorage.setItem(BANNER_DISMISS_KEY, "1");
    } catch {
      /* private mode / no storage — banner just disappears for the session */
    }
    onDismiss?.();
  };

  return (
    <div className="border-b border-border-soft bg-surface-elev px-4 py-2.5 flex flex-wrap items-center gap-2 sm:gap-3 text-[12.5px]">
      <span className="order-1 flex-1 text-text-muted">
        还没接上电脑？把这条命令粘进终端：
      </span>
      <code className="order-3 sm:order-2 font-mono text-[12.5px] text-text bg-bg/50 px-2 py-1 rounded border border-border-soft whitespace-nowrap overflow-x-auto flex-1 min-w-0">
        {command}
      </code>
      <button
        type="button"
        onClick={copy}
        className="order-4 sm:order-3 shrink-0 px-2.5 py-1 rounded text-[12px] font-medium bg-text text-bg hover:opacity-90 transition"
      >
        {copied ? "已复制" : "复制"}
      </button>
      <button
        type="button"
        onClick={dismiss}
        aria-label="知道了，关闭"
        title="知道了"
        className="order-2 sm:order-4 shrink-0 w-6 h-6 grid place-items-center rounded text-text-dim hover:text-text hover:bg-surface-hover text-[14px] leading-none"
      >
        ✕
      </button>
    </div>
  );
}

export function isConnectBannerDismissed(): boolean {
  try {
    return window.localStorage.getItem(BANNER_DISMISS_KEY) === "1";
  } catch {
    return false;
  }
}
