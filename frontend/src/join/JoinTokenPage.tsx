import { useEffect, useState } from "react";
import type { FormEvent } from "react";

interface Props {
  token: string;
}

interface InviteAcceptResponse {
  workspace_id: number;
  topic_id?: number | null;
}

function redirectAfterAccept(data: InviteAcceptResponse) {
  const params = new URLSearchParams({ workspace: String(data.workspace_id) });
  if (data.topic_id) params.set("topic", String(data.topic_id));
  window.location.href = `/?${params.toString()}`;
}

export function JoinTokenPage({ token }: Props) {
  const [name, setName] = useState("");
  const [checkingSession, setCheckingSession] = useState(true);
  const [joining, setJoining] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const acceptAsCurrentUser = () => {
    fetch(`/api/invites/${token}/accept`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
    })
      .then(async (res) => {
        if (!res.ok) throw new Error("failed");
        return res.json() as Promise<InviteAcceptResponse>;
      })
      .then((data) => {
        redirectAfterAccept(data);
      })
      .catch(() => {
        setCheckingSession(false);
        setError("邀请链接无效或已过期");
      });
  };

  useEffect(() => {
    fetch("/auth/me", { credentials: "include" })
      .then((res) => {
        const contentType = res.headers.get("content-type") ?? "";
        if (res.ok && contentType.includes("application/json")) {
          acceptAsCurrentUser();
          return;
        }
        setCheckingSession(false);
      })
      .catch(() => setCheckingSession(false));
  }, [token]);

  const joinAsGuest = (event: FormEvent) => {
    event.preventDefault();
    const displayName = name.trim();
    if (!displayName) return;
    setJoining(true);
    setError(null);
    fetch(`/api/invites/${token}/accept-guest`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ name: displayName }),
    })
      .then(async (res) => {
        if (!res.ok) throw new Error("failed");
        return res.json() as Promise<InviteAcceptResponse>;
      })
      .then((data) => {
        redirectAfterAccept(data);
      })
      .catch(() => {
        setJoining(false);
        setError("邀请链接无效或已过期");
      });
  };

  if (checkingSession) {
    return (
      <div className="grid place-items-center min-h-screen text-sm text-text-dim">
        加入工作区中…
      </div>
    );
  }

  return (
    <div className="min-h-screen grid place-items-center bg-bg px-6">
      <div className="w-full max-w-sm flex flex-col gap-6">
        <div className="text-center flex flex-col gap-2">
          <h1 className="font-[var(--font-display)] text-3xl text-text">加入聊天</h1>
          <p className="text-sm text-text-dim">输入一个显示名，就可以作为访客参与讨论。</p>
        </div>
        <form onSubmit={joinAsGuest} className="flex flex-col gap-3">
          <label className="text-xs text-text-dim" htmlFor="guest-name">
            你的名字
          </label>
          <input
            id="guest-name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            maxLength={40}
            autoFocus
            className="w-full rounded-md border border-border bg-bg px-3 py-2 text-sm text-text outline-none focus:border-text"
          />
          <button
            type="submit"
            disabled={!name.trim() || joining}
            className="inline-flex items-center justify-center rounded-md bg-text px-4 py-2.5 text-sm font-medium text-bg disabled:opacity-50"
          >
            {joining ? "加入中…" : "作为访客加入"}
          </button>
        </form>
        <a
          href={`/auth/github/start?next=/join/${encodeURIComponent(token)}`}
          className="inline-flex items-center justify-center rounded-md border border-border px-4 py-2.5 text-sm text-text hover:bg-hover"
        >
          用 GitHub 继续
        </a>
        {error && <p className="text-center text-xs text-red-500">{error}</p>}
      </div>
    </div>
  );
}
