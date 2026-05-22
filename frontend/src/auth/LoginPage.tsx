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
      <div className="max-w-xs w-full px-6 text-center flex flex-col gap-8">
        <h1 className="font-[var(--font-display)] text-4xl">Let's</h1>
        <a
          href={loginHref}
          className="inline-flex items-center justify-center px-4 py-2.5 rounded-lg bg-text text-bg text-sm font-medium"
        >
          {label}
        </a>
        {devLogin && (
          <p className="text-[11px] text-text-dim">本地开发登录</p>
        )}
      </div>
    </div>
  );
}
