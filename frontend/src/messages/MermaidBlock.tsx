import { useEffect, useRef, useState } from "react";
import { openDiagram } from "./openDiagram";

let initialized = false;
async function ensureMermaid() {
  const mod = await import("mermaid");
  const mermaid = mod.default;
  if (!initialized) {
    mermaid.initialize({
      startOnLoad: false,
      securityLevel: "loose",
      theme: "base",
      themeVariables: {
        background:        "#FBF9F4",
        primaryColor:      "#F3E4DA",
        primaryBorderColor:"#B4654A",
        primaryTextColor:  "#2C2A26",
        lineColor:         "#8E3B2E",
        secondaryColor:    "#ECEFD9",
        tertiaryColor:     "#DEE7EC",
        fontFamily:        "Source Serif 4, Newsreader, serif",
      },
    });
    initialized = true;
  }
  return mermaid;
}

let renderCounter = 0;

/**
 * Lazily renders a mermaid source block to inline SVG. The mermaid lib
 * is dynamically imported the first time any block appears in the page,
 * so non-mermaid chat conversations never pay its bundle cost.
 */
export function MermaidBlock({
  source,
  fromMsgId,
  topicId,
}: {
  source: string;
  /** When provided, clicking the block opens the full-screen overlay. */
  fromMsgId?: number;
  /** Topic id — forwarded to the overlay so node-level annotations can post. */
  topicId?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const id = `mmd-${++renderCounter}`;
    (async () => {
      try {
        const mermaid = await ensureMermaid();
        const { svg } = await mermaid.render(id, source);
        if (!cancelled && ref.current) {
          ref.current.innerHTML = svg;
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      }
    })();
    return () => { cancelled = true; };
  }, [source]);

  if (error) {
    return (
      <div className="my-2 border border-finding rounded p-2 text-[12px] text-finding font-mono">
        mermaid 渲染失败：{error.split("\n")[0]}
        <pre className="mt-1 text-text whitespace-pre-wrap">{source}</pre>
      </div>
    );
  }

  const clickable = typeof fromMsgId === "number";
  return (
    <div
      role={clickable ? "button" : undefined}
      tabIndex={clickable ? 0 : undefined}
      onClick={
        clickable
          ? () => openDiagram({ source, fromMsgId: fromMsgId as number, label: "diagram", topicId })
          : undefined
      }
      onKeyDown={
        clickable
          ? (e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                openDiagram({ source, fromMsgId: fromMsgId as number, label: "diagram", topicId });
              }
            }
          : undefined
      }
      title={clickable ? "点击放大查看" : undefined}
      className={
        "my-2 border border-border-soft rounded bg-surface-elev px-3 py-3 relative overflow-x-auto" +
        (clickable
          ? " cursor-zoom-in hover:border-accent-border transition-colors group"
          : "")
      }
    >
      <span className="absolute top-1.5 right-2 font-mono text-[10px] text-text-dim bg-bg/70 px-1.5 rounded border border-border-soft uppercase tracking-[0.04em]">
        {clickable ? (
          <span className="group-hover:text-accent-text">点击放大</span>
        ) : (
          "mermaid"
        )}
      </span>
      <div ref={ref} aria-label="mermaid diagram" />
    </div>
  );
}
