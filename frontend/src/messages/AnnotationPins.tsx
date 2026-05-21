import { useMemo } from "react";
import { useStream } from "./StreamContext";
import { usePostMessage, useSessionMe } from "../api/queries";

interface AnnotationItem {
  id: number;
  body: string;
  quote: string;
  actorId: number | null;
  actorType: "human" | "agent" | "system";
  createdAt: string;
  resolved: boolean;
}

function extractAnnotation(meta: unknown): { target: number; quote: string; resolved: boolean } | null {
  if (typeof meta !== "object" || meta === null) return null;
  const m = meta as Record<string, unknown>;
  const target = m.target_message_id;
  if (typeof target !== "number") return null;
  // Score annotations (metadata.score = ±1) are rendered as a vote badge,
  // not as a sticky-note pin. Skip them here.
  if (typeof m.score === "number") return null;
  const quote = typeof m.target_quote === "string" ? m.target_quote : "";
  const resolved = m.resolved === true;
  return { target, quote, resolved };
}

/**
 * Render every unresolved/resolved annotation targeting `messageId` as a
 * sticky-note row below the message body. Source of truth is the chat
 * stream — annotations are typed messages of type `annotation`, so the
 * StreamProvider already has them in `byId`.
 */
export function AnnotationPins({
  topicId,
  messageId,
}: { topicId: number; messageId: number }) {
  const { byId, resolveActor } = useStream();
  const post = usePostMessage(topicId);
  const me = useSessionMe();

  const items = useMemo<AnnotationItem[]>(() => {
    const out: AnnotationItem[] = [];
    for (const m of byId.values()) {
      if (m.type !== "annotation") continue;
      const ann = extractAnnotation(m.metadata);
      if (!ann || ann.target !== messageId) continue;
      out.push({
        id: m.id,
        body: m.body,
        quote: ann.quote,
        actorId: m.actor_id,
        actorType: m.actor_type,
        createdAt: m.created_at,
        resolved: ann.resolved,
      });
    }
    out.sort((a, b) => a.id - b.id);
    return out;
  }, [byId, messageId]);

  if (items.length === 0) return null;

  async function resolve(id: number) {
    const orig = byId.get(id);
    if (!orig || !me.data) return;
    // Post a follow-up annotation that flips resolved=true. We could also
    // PATCH, but typed-message-only ops are simpler and keep history.
    await post.mutateAsync({
      topic_id: topicId,
      type: "annotation",
      actor_type: "human",
      actor_id: me.data.human.id,
      body: "(已解决)",
      metadata: {
        target_message_id: messageId,
        target_quote: extractAnnotation(orig.metadata)?.quote || "",
        resolved: true,
        resolves: id,
      },
    });
  }

  // Treat an annotation as resolved if there's a later annotation on the
  // same message with metadata.resolves = this id.
  const resolvedIds = new Set<number>();
  for (const m of byId.values()) {
    if (m.type !== "annotation") continue;
    const meta = m.metadata as Record<string, unknown>;
    if (meta.resolved === true && typeof meta.resolves === "number") {
      resolvedIds.add(meta.resolves);
    }
  }

  return (
    <div className="mt-2 flex flex-col gap-1.5">
      {items
        .filter((a) => a.body !== "(已解决)")  // hide the resolve marker rows
        .map((a) => {
          const isResolved = a.resolved || resolvedIds.has(a.id);
          const actor = resolveActor({
            id: a.id, topic_id: topicId, type: "annotation",
            actor_type: a.actorType, actor_id: a.actorId,
            body: a.body, metadata: {}, ref_event_id: null,
            created_at: a.createdAt,
          });
          return (
            <div
              key={a.id}
              className={[
                "border-l-[3px] rounded-r pl-3 pr-2 py-2 text-[12.5px]",
                isResolved
                  ? "border-text-dim/40 bg-surface/60 opacity-60"
                  : "border-annotation bg-annotation-bg",
              ].join(" ")}
            >
              <div className="flex items-baseline gap-2">
                <span className="font-mono text-[10.5px] text-text-muted font-semibold uppercase tracking-[0.04em]">
                  批注 · {actor.displayName}
                </span>
                {isResolved && (
                  <span className="font-mono text-[10px] text-text-dim italic">已解决</span>
                )}
                {!isResolved && (
                  <button
                    type="button"
                    onClick={() => resolve(a.id)}
                    className="ml-auto text-[10.5px] text-text-dim hover:text-text italic underline decoration-dotted"
                  >标为已解决</button>
                )}
              </div>
              {a.quote && (
                <div className="text-[11.5px] text-text-dim italic mt-1 border-l border-border-soft pl-2">
                  “{a.quote.length > 100 ? a.quote.slice(0, 100) + "…" : a.quote}”
                </div>
              )}
              <div className="mt-1 text-text leading-relaxed">{a.body}</div>
            </div>
          );
        })}
    </div>
  );
}
