const LEADING_PATTERNS = [
  /^@[\p{L}\p{N}_-]+\s*/u,
  /^(有人在吗|在吗|有人吗)[？?，,\s]*/iu,
  /^(我想|想|我们来|我们想|帮我|请帮我)\s*/iu,
  /^(讨论|聊聊|聊一下|做|设计|开发|构建|实现|研究|规划)\s*/iu,
  /^(一个|一款|一种|一下)\s*/iu,
];

export function summarizeTopicIntent(body: string, maxLen = 28): string {
  let text = (body || "").trim().split(/\n/, 1)[0]?.trim() ?? "";
  text = text.replace(/\s+/g, " ");
  for (const pattern of LEADING_PATTERNS) {
    text = text.replace(pattern, "").trim();
  }

  const match = text.match(/支持(.+?)的(.+)$/u);
  if (match?.[1] && match[2]) {
    text = `${match[1].trim()}${match[2].trim()}`;
  }

  text = text.replace(/[。.!！?？]+$/u, "").trim();
  return text.length > maxLen ? `${text.slice(0, maxLen)}…` : text;
}

export function summarizeTopicGoal(body: string, maxLen = 80): string {
  const title = summarizeTopicIntent(body, maxLen);
  if (!title) return "";
  return /工具|系统|app|App|应用|平台/u.test(title)
    ? `讨论并设计「${title}」的目标、方案和风险`
    : `讨论并明确「${title}」`;
}
