import type { MessageDTO, TopicDTO } from "../api/types";

const GENERIC_TITLES = new Set([
  "new",
  "新对话",
  "untitled",
  "topic",
  "主频道",  // auto-created on first login; fall through to first-message title
  "general",
]);

function cleanFirstLine(body: string): string {
  // Strip leading @mention so titles aren't dominated by "@cc ..."
  return body.trim().replace(/^@[\p{L}\p{N}_-]+\s*/u, "").trim();
}

export function topicDisplayTitle(topic: TopicDTO | undefined, messages: MessageDTO[]): string {
  const rawTitle = topic?.title?.trim();
  if (rawTitle && !GENERIC_TITLES.has(rawTitle.toLowerCase())) return rawTitle;

  const firstHuman = messages.find((m) => m.actor_type === "human" && m.type === "chat");
  if (!firstHuman) return rawTitle || "新对话";

  const body = firstHuman.body.trim();
  if (/^@?(cc|claude)\s*在吗[？?]?$/i.test(body)) return "等待 CC 回复";
  if (/^@?(cx|codex)\s*在吗[？?]?$/i.test(body)) return "等待 Codex 回复";

  const clean = cleanFirstLine(body);
  return clean.length > 28 ? `${clean.slice(0, 28)}…` : clean;
}
