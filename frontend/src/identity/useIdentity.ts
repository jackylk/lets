import { createContext, useContext } from "react";

export interface Identity {
  humanName: string | null;
  agentRole: string | null;
  deviceLabel: string | null;
}
export interface IdentityContextValue extends Identity {
  setIdentity: (next: Partial<Identity>) => void;
}
export const IdentityContext = createContext<IdentityContextValue | null>(null);

export function useIdentity(): IdentityContextValue {
  const ctx = useContext(IdentityContext);
  if (!ctx) throw new Error("useIdentity must be used inside <IdentityProvider />");
  return ctx;
}
