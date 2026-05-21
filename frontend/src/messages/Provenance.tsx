import { useStream } from "./StreamContext";

/**
 * "基于 [J] 我们要给… [CC] 好的，先把约束…" — the row above an agent
 * reply that shows which messages the agent had in its prompt. Hover any
 * chip (or the row) → those messages get highlighted in the stream. Click
 * a chip → smooth-scrolls to that message.
 */
export function Provenance({ cites }: { cites: number[] }) {
  const { byId, resolveActor, setHighlighted, clearHighlight } = useStream();

  if (!cites || cites.length === 0) return null;

  function setAll() { setHighlighted(cites); }

  return (
    <div
      data-testid="provenance"
      className="my-1.5 flex flex-wrap items-center gap-1.5 text-[11px] text-text-dim"
      onMouseEnter={setAll}
      onMouseLeave={clearHighlight}
    >
      <span className="font-mono text-[10.5px] uppercase tracking-[0.04em]">基于</span>
      {cites.map((cid) => {
        const m = byId.get(cid);
        if (!m) {
          return (
            <span
              key={cid}
              className="text-text-dim italic text-[11px]"
            >#{cid}（已不可见）</span>
          );
        }
        const actor = resolveActor(m);
        const snippet = (m.body || "").trim().split("\n", 1)[0]?.slice(0, 18) || "";
        return (
          <button
            key={cid}
            type="button"
            data-cite={cid}
            onMouseEnter={(e) => { e.stopPropagation(); setHighlighted([cid]); }}
            onMouseLeave={(e) => { e.stopPropagation(); setAll(); }}
            onClick={() => {
              document
                .querySelector(`[data-msg-id="${cid}"]`)
                ?.scrollIntoView({ behavior: "smooth", block: "center" });
            }}
            className={[
              "inline-flex items-center gap-1.5 max-w-[220px]",
              "px-2 py-[2px] pr-2.5 rounded-[3px] border bg-surface-elev border-border-soft",
              "text-[11px] text-text-muted hover:bg-accent-soft hover:border-accent-border hover:text-accent-text",
              "transition-colors",
            ].join(" ")}
          >
            <span
              className={[
                "inline-grid place-items-center w-4 h-4 rounded-[2px] border font-[var(--font-display)] font-bold text-[9px]",
                actor.kind === "human"
                  ? "border-human/40 text-human bg-human-bg"
                  : "border-accent-border text-accent-text bg-accent-soft",
              ].join(" ")}
            >{actor.initial}</span>
            <span className="truncate min-w-0">{snippet || "(无内容)"}{snippet && (m.body || "").length > 18 ? "…" : ""}</span>
          </button>
        );
      })}
    </div>
  );
}
