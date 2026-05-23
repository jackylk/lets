from __future__ import annotations

import re


_LEADING_PATTERNS = [
    r"^@[\w\u4e00-\u9fff-]+\s*",
    r"^(有人在吗|在吗|有人吗)[？?，,\s]*",
    r"^(我想|想|我们来|我们想|帮我|请帮我)\s*",
    r"^(讨论|聊聊|聊一下|做|设计|开发|构建|实现|研究|规划)\s*",
    r"^(一个|一款|一种|一下)\s*",
]


def summarize_topic_intent(body: str, *, max_len: int = 28) -> str:
    """Derive a compact product/topic label from a user opening message.

    This is the deterministic fallback before an agent posts a formal
    goal_proposal. It avoids using the whole first sentence as the title.
    """
    text = (body or "").strip()
    text = text.split("\n", 1)[0].strip()
    text = re.sub(r"\s+", " ", text)
    for pattern in _LEADING_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE).strip()

    # Common Chinese opening: "讨论一个支持 X 的 Y" -> "X Y" when that reads
    # better as a compact title, e.g. "支持自然语言的文件检索工具".
    m = re.search(r"支持(.+?)的(.+)$", text)
    if m:
        capability = m.group(1).strip()
        subject = m.group(2).strip()
        if capability and subject:
            text = f"{capability}{subject}"

    text = re.sub(r"[。.!！?？]+$", "", text).strip()
    if not text:
        return ""
    return text if len(text) <= max_len else text[:max_len] + "…"


def summarize_topic_goal(body: str, *, max_len: int = 80) -> str:
    title = summarize_topic_intent(body, max_len=max_len)
    if not title:
        return ""
    if any(word in title for word in ("工具", "系统", "app", "App", "应用", "平台")):
        return f"讨论并设计「{title}」的目标、方案和风险"
    return f"讨论并明确「{title}」"
