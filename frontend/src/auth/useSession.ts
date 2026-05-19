import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "../api/client";

export interface SessionUser {
  id: number;
  name: string;
  github_login: string | null;
  avatar_url: string | null;
}

export interface SessionResponse { human: SessionUser }

export function useSession() {
  return useQuery({
    queryKey: ["auth.me"],
    queryFn: async () => {
      try {
        return await apiRequest<SessionResponse>("/auth/me", {
          identity: { humanName: null, agentRole: null, deviceLabel: null },
        });
      } catch (e) {
        if (e instanceof Error && /401/.test(e.message)) return null;
        throw e;
      }
    },
    retry: false,
    staleTime: 60_000,
  });
}
