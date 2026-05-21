/**
 * Backend stores ``CURRENT_TIMESTAMP`` from SQLite which is UTC but emitted
 * without a timezone marker (``2026-05-20 09:41:00``). ``new Date(iso)`` then
 * parses it as *local* time, so the display ends up 8 hours behind in
 * Beijing. Normalize: if the string lacks a TZ marker, treat it as UTC by
 * appending ``Z`` (and converting the space separator to ``T`` so Safari
 * accepts it too).
 */
export function parseBackendTs(iso: string): Date {
  let s = iso;
  if (s.includes(" ") && !s.includes("T")) s = s.replace(" ", "T");
  if (!/[zZ]|[+-]\d{2}:?\d{2}$/.test(s)) s = s + "Z";
  return new Date(s);
}

export function formatHHMM(iso: string): string {
  const d = parseBackendTs(iso);
  return d.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", hour12: false });
}
