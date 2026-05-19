import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { IdentityContext, type Identity } from "./useIdentity";
import { useSession } from "../auth/useSession";

const STORAGE_KEY = "lets.identity";

function loadIdentity(): Identity {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { humanName: null, agentRole: null, deviceLabel: null };
    const parsed = JSON.parse(raw) as Partial<Identity>;
    return {
      humanName: parsed.humanName ?? null,
      agentRole: parsed.agentRole ?? null,
      deviceLabel: parsed.deviceLabel ?? null,
    };
  } catch {
    return { humanName: null, agentRole: null, deviceLabel: null };
  }
}

export function IdentityProvider({ children }: { children: ReactNode }) {
  const [identity, setIdentityState] = useState<Identity>(() => loadIdentity());
  const session = useSession();

  // When session is known, override humanName from the server (source of truth).
  useEffect(() => {
    if (session.data?.human?.name && session.data.human.name !== identity.humanName) {
      setIdentityState((prev) => {
        const next = { ...prev, humanName: session.data!.human.name };
        localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
        return next;
      });
    }
  }, [session.data, identity.humanName]);

  const setIdentity = useCallback((next: Partial<Identity>) => {
    setIdentityState((prev) => {
      const merged: Identity = { ...prev, ...next };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(merged));
      return merged;
    });
  }, []);

  const value = useMemo(() => ({ ...identity, setIdentity }), [identity, setIdentity]);
  return <IdentityContext.Provider value={value}>{children}</IdentityContext.Provider>;
}
