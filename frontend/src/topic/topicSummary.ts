import type { MessageDTO, TopicDTO } from "../api/types";
import { summarizeTopicIntent } from "./intentSummary";

const GENERIC_TITLES = new Set([
  "new",
  "新对话",
  "新话题",  // auto-created on first login; fall through to first-message title
  "untitled",
  "topic",
  "主频道",  // legacy default; kept for back-compat
  "general",
]);

export function topicDisplayTitle(topic: TopicDTO | undefined, messages: MessageDTO[]): string {
  const rawTitle = topic?.title?.trim();
  if (rawTitle && !GENERIC_TITLES.has(rawTitle.toLowerCase())) return rawTitle;

  const firstHuman = messages.find((m) => m.actor_type === "human" && m.type === "chat");
  if (!firstHuman) return rawTitle || "新对话";

  const body = firstHuman.body.trim();
  if (/^@?(cc|claude)\s*在吗[？?]?$/i.test(body)) return "等待 CC 回复";
  if (/^@?(cx|codex)\s*在吗[？?]?$/i.test(body)) return "等待 Codex 回复";

  return summarizeTopicIntent(body) || rawTitle || "新对话";
}
