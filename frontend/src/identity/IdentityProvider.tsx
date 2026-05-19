import { useCallback, useMemo, useState, type ReactNode } from "react";
import { IdentityContext, type Identity } from "./useIdentity";

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
