import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "../api/client";

interface ContextResponse {
  auth?: {
    dev_login_enabled?: boolean;
    github_configured?: boolean;
  };
}

const features = [
  {
    title: "并行协作",
    description: "在同一个讨论里，多个 coding agent 和人类可以同步推进任务。",
  },
  {
    title: "上下文面板",
    description: "任务、决定、spec、artifact 一起展示，避免来回切页。",
  },
  {
    title: "随时加入",
    description: "发起邀请后，成员可通过链接快速加入到 workspace。",
  },
];

export function HomePage() {
  const context = useQuery({
    queryKey: ["public-context"],
    queryFn: () =>
      apiRequest<ContextResponse>("/api/context", {
        identity: { humanName: null, agentRole: null, deviceLabel: null },
      }),
    retry: false,
  });

  const auth = context.data?.auth;
  const devLogin = auth?.dev_login_enabled === true;
  const loginHref = devLogin ? "/auth/dev/login?human=Neo&next=/app" : "/auth/github/start";
  const loginLabel = devLogin ? "本地快速体验" : "立即用 GitHub 登录";

  return (
    <div className="min-h-screen bg-bg text-text">
      <main className="mx-auto flex min-h-screen w-full max-w-6xl flex-col gap-8 px-6 py-10">
        <section className="rounded-[10px] border border-border bg-surface p-7 md:p-10">
          <p className="text-xs uppercase tracking-[0.18em] text-text-muted">Let's | 聊天搭子</p>
          <h1 className="mt-2 text-4xl font-semibold leading-tight">把讨论变成可持续推进的协作动作</h1>
          <p className="mt-4 max-w-2xl text-lg text-text-muted">
            Let's 聚焦多人协作中的“任务—结论—产出”闭环，帮助你把多轮对话整理成可执行的工作流。
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <a
              href={loginHref}
              className="inline-flex items-center rounded-lg bg-text px-4 py-2.5 text-sm font-medium text-bg"
            >
              {loginLabel}
            </a>
            <a
              href="#features"
              className="inline-flex items-center rounded-lg border border-border bg-surface-elev px-4 py-2.5 text-sm font-medium"
            >
              了解加入方式
            </a>
          </div>
          {context.isLoading && (
            <p className="mt-4 text-xs text-text-muted">正在加载登录方式…</p>
          )}
        </section>

        <section id="features" className="grid gap-4 md:grid-cols-3">
          {features.map((item) => (
            <article
              key={item.title}
              className="rounded-[10px] border border-border bg-surface-elev p-5"
            >
              <h2 className="mb-2 text-lg font-medium">{item.title}</h2>
              <p className="text-sm text-text-muted leading-relaxed">{item.description}</p>
            </article>
          ))}
        </section>
      </main>
    </div>
  );
}
