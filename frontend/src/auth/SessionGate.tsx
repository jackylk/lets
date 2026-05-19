import type { ReactNode } from "react";
import { useSession } from "./useSession";

interface Props {
  children: ReactNode;
  fallback: ReactNode;
}

export function SessionGate({ children, fallback }: Props) {
  const q = useSession();
  if (q.isLoading) {
    return <div className="min-h-screen grid place-items-center text-text-dim">…</div>;
  }
  if (!q.data) return <>{fallback}</>;
  return <>{children}</>;
}
