import type { Identity } from "../identity/useIdentity";

export class ApiError extends Error {
  constructor(public status: number, public body: unknown) {
    super(`Let's API ${status}`);
  }
}

export function identityHeaders(identity: Identity): Record<string, string> {
  const h: Record<string, string> = {};
  if (identity.humanName) h["X-Lets-Human"] = identity.humanName;
  if (identity.agentRole) h["X-Lets-Agent-Role"] = identity.agentRole;
  if (identity.deviceLabel) h["X-Lets-Device"] = identity.deviceLabel;
  return h;
}

export interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  rawBody?: BodyInit;
  contentType?: string | null;
  identity: Identity;
  query?: Record<string, string | string[] | undefined>;
}

function apiUrl(path: string, query?: RequestOptions["query"]) {
  const url = new URL(path, window.location.origin);
  if (query) {
    for (const [k, v] of Object.entries(query)) {
      if (v === undefined) continue;
      if (Array.isArray(v)) v.forEach((x) => url.searchParams.append(k, x));
      else url.searchParams.set(k, v);
    }
  }
  return url;
}

export async function apiRequest<T>(path: string, opts: RequestOptions): Promise<T> {
  const url = apiUrl(path, opts.query);
  const headers: Record<string, string> = { ...identityHeaders(opts.identity) };
  let body: BodyInit | undefined;
  if (opts.rawBody !== undefined) {
    body = opts.rawBody;
    if (opts.contentType) headers["Content-Type"] = opts.contentType;
  } else if (opts.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opts.body);
  }

  const res = await fetch(url.toString(), {
    method: opts.method ?? "GET",
    headers,
    body,
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

export async function apiBlobRequest(path: string, opts: RequestOptions): Promise<Blob> {
  const res = await fetch(apiUrl(path, opts.query).toString(), {
    method: opts.method ?? "GET",
    headers: identityHeaders(opts.identity),
  });
  if (!res.ok) {
    let body: unknown = null;
    try { body = await res.json(); } catch { /* ignore */ }
    throw new ApiError(res.status, body);
  }
  return res.blob();
}
