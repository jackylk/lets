"""Per-topic in-process broadcast queues for SSE live updates.

v1.5b uses a single-process asyncio.Queue per topic. Multi-replica
deployments (Railway Track I) will swap this for Postgres LISTEN/NOTIFY
or Redis pub/sub without changing the public API.
"""
from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any


class TopicBroadcaster:
    def __init__(self) -> None:
        self._subs: dict[int, list[asyncio.Queue]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def subscribe(self, topic_id: int) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=256)
        async with self._lock:
            self._subs[topic_id].append(q)
        return q

    def unsubscribe(self, topic_id: int, queue: asyncio.Queue) -> None:
        subs = self._subs.get(topic_id, [])
        if queue in subs:
            subs.remove(queue)
        if not subs and topic_id in self._subs:
            del self._subs[topic_id]

    async def publish(self, topic_id: int, payload: dict[str, Any]) -> None:
        for q in list(self._subs.get(topic_id, [])):
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                pass


broadcaster = TopicBroadcaster()
