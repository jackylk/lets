import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "../api/client";

interface ContextResponse {
  auth?: {
    dev_login_enabled?: boolean;
    github_configured?: boolean;
  };
}

export function LoginPage({ initialContext }: { initialContext?: ContextResponse } = {}) {
  const context = useQuery({
    queryKey: ["public-context"],
    queryFn: () =>
      apiRequest<ContextResponse>("/api/context", {
        identity: { humanName: null, agentRole: null, deviceLabel: null },
      }),
    enabled: initialContext === undefined,
    retry: false,
  });
  const auth = initialContext?.auth ?? context.data?.auth;
  // Trust the server flag exclusively. Dev login is only available when the
  // backend was started with LETS_DEV_SESSIONS=1 — host-based detection
  // would override real OAuth setups even when the operator explicitly
  // disabled the dev path.
  const devLogin = auth?.dev_login_enabled === true;
  const loginHref = devLogin ? "/auth/dev/login?human=Neo&next=/app" : "/auth/github/start";
  const label = devLogin ? "Continue as Neo" : "Sign in with GitHub";

  return (
    <div className="min-h-screen grid place-items-center bg-bg">
      <div className="max-w-sm w-full px-6 py-10 text-center flex flex-col gap-6">
        <div>
          <h1 className="font-[var(--font-display)] text-3xl">Lets</h1>
          <p className="text-text-muted text-sm mt-2">协同工作空间 · 你和你的 agent</p>
        </div>
        <a
          href={loginHref}
          className="inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-text text-bg font-medium"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 .5C5.65.5.5 5.65.5 12c0 5.08 3.29 9.39 7.86 10.91.58.1.79-.25.79-.55 0-.27-.01-1-.02-1.95-3.2.7-3.87-1.54-3.87-1.54-.52-1.32-1.27-1.67-1.27-1.67-1.04-.71.08-.7.08-.7 1.15.08 1.76 1.18 1.76 1.18 1.02 1.75 2.68 1.25 3.34.96.1-.74.4-1.25.73-1.54-2.55-.29-5.24-1.28-5.24-5.69 0-1.26.45-2.28 1.18-3.09-.12-.29-.51-1.46.11-3.05 0 0 .97-.31 3.18 1.18a11 11 0 0 1 5.79 0c2.21-1.49 3.18-1.18 3.18-1.18.62 1.59.23 2.76.11 3.05.74.81 1.18 1.83 1.18 3.09 0 4.42-2.69 5.4-5.25 5.68.41.36.78 1.05.78 2.12 0 1.53-.01 2.77-.01 3.15 0 .31.21.66.8.55C20.21 21.39 23.5 17.08 23.5 12 23.5 5.65 18.35.5 12 .5Z"/>
          </svg>
          {label}
        </a>
        {devLogin ? (
          <p className="text-[11px] text-text-dim">
            本地开发登录已开启。生产环境仍会使用 GitHub OAuth。
          </p>
        ) : (
          <p className="text-[11px] text-text-dim">
            没有 GitHub 账号？联系工作区管理员用 CLI 给你开个 token：
            <code className="font-mono ml-1">python -m app.tokens_cli issue --human &lt;name&gt;</code>
          </p>
        )}
      </div>
    </div>
  );
}
