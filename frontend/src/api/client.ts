import type { Identity } from "../identity/useIdentity";

export class ApiError extends Error {
  constructor(public status: number, public body: unknown) {
    super(`Lets API ${status}`);
  }
}

function identityHeaders(identity: Identity): Record<string, string> {
  const h: Record<string, string> = {};
  if (identity.humanName) h["X-Lets-Human"] = identity.humanName;
  if (identity.agentRole) h["X-Lets-Agent-Role"] = identity.agentRole;
  if (identity.deviceLabel) h["X-Lets-Device"] = identity.deviceLabel;
  return h;
}

export interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  identity: Identity;
  query?: Record<string, string | string[] | undefined>;
}

export async function apiRequest<T>(path: string, opts: RequestOptions): Promise<T> {
  const url = new URL(path, window.location.origin);
  if (opts.query) {
    for (const [k, v] of Object.entries(opts.query)) {
      if (v === undefined) continue;
      if (Array.isArray(v)) v.forEach((x) => url.searchParams.append(k, x));
      else url.searchParams.set(k, v);
    }
  }
  const res = await fetch(url.toString(), {
    method: opts.method ?? "GET",
    headers: { "Content-Type": "application/json", ...identityHeaders(opts.identity) },
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  if (!res.ok) {
    let body: unknown = null;
    try { body = await res.json(); } catch { /* ignore */ }
    throw new ApiError(res.status, body);
  }
  const ct = res.headers.get("content-type") ?? "";
  if (!ct.includes("application/json")) return null as T;
  return (await res.json()) as T;
}
