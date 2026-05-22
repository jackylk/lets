import { useEffect, useState } from "react";

interface Props {
  token: string;
}

export function JoinTokenPage({ token }: Props) {
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    fetch(`/api/invites/${token}/accept`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
    })
      .then(async (res) => {
        if (!res.ok) throw new Error("failed");
        return res.json() as Promise<{ workspace_id: number }>;
      })
      .then((data) => {
        window.location.href = `/?workspace=${data.workspace_id}`;
      })
      .catch(() => setError("邀请链接无效或已过期"));
  }, [token]);
  return (
    <div className="grid place-items-center min-h-screen text-sm text-text-dim">
      {error ?? "加入工作区中…"}
    </div>
  );
}
