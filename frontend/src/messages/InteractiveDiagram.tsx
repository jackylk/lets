import { useEffect, useMemo, useRef, useState } from "react";

let mermaidInitialized = false;
async function ensureMermaid() {
  const mod = await import("mermaid");
  const mermaid = mod.default;
  if (!mermaidInitialized) {
    mermaid.initialize({
      startOnLoad: false,
      securityLevel: "loose",
      theme: "base",
      themeVariables: {
        background: "#FBF9F4",
        primaryColor: "#F3E4DA",
        primaryBorderColor: "#B4654A",
        primaryTextColor: "#2C2A26",
        lineColor: "#8E3B2E",
        secondaryColor: "#ECEFD9",
        tertiaryColor: "#DEE7EC",
        fontFamily: "Source Serif 4, Newsreader, serif",
      },
    });
    mermaidInitialized = true;
  }
  return mermaid;
}

let renderCounter = 0;

interface SelectedNode {
  text: string;
  cx: number;
  cy: number;
}

/**
 * Renders a mermaid diagram inside the overlay and lets the user select a
 * node (mindmap / graph / flow) for inline feedback. Node identity = the
 * trimmed text content of the node, which the overlay's feedback panel
 * uses as `metadata.target_quote` when posting annotations. Stays separate
 * from `MermaidBlock` so the inline-chat block stays simple.
 *
 * When a node is clicked, `onSelect` fires with the node text and the
 * node's center coordinates (in container space) so the caller can
 * position a small selection-highlight marker.
 */
export function InteractiveDiagram({
  source,
  onSelect,
  selectedText,
  votedTextsByDir,
}: {
  source: string;
  onSelect: (sel: SelectedNode | null) => void;
  /** Currently selected node text (for visual highlight). */
  selectedText: string | null;
  /** Node text → net score, for showing badges in-graph. */
  votedTextsByDir: Map<string, number>;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [, forceTick] = useState(0); // re-run handler attach after re-render

  // Render mermaid → innerHTML.
  useEffect(() => {
    let cancelled = false;
    const id = `mmd-i-${++renderCounter}`;
    (async () => {
      try {
        const mermaid = await ensureMermaid();
        const { svg } = await mermaid.render(id, source);
        if (cancelled || !ref.current) return;
        ref.current.innerHTML = svg;
        forceTick((n) => n + 1);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [source]);

  // Attach click handlers to every node element mermaid produced. Mermaid
  // uses `g.node` for graph/flowchart/sequence and `g.mindmap-node` for
  // mindmaps; we accept both. Identity = trimmed text content.
  useEffect(() => {
    const root = ref.current;
    if (!root) return;
    const svg = root.querySelector("svg");
    if (!svg) return;
    const nodes = svg.querySelectorAll<SVGGElement>(
      "g.node, g.mindmap-node, g[class*='mindmap-node']",
    );
    const cleanups: Array<() => void> = [];

    nodes.forEach((node) => {
      const text = (node.textContent || "").trim();
      if (!text) return;
      node.style.cursor = "pointer";
      const onClick = (e: Event) => {
        e.stopPropagation();
        // Compute center in container coords.
        const bbox = node.getBoundingClientRect();
        const rootBox = root.getBoundingClientRect();
        const cx = bbox.left - rootBox.left + bbox.width / 2;
        const cy = bbox.top - rootBox.top + bbox.height / 2;
        onSelect({ text, cx, cy });
      };
      node.addEventListener("click", onClick);
      cleanups.push(() => node.removeEventListener("click", onClick));

      // Selection highlight: stroke the shape inside the node group.
      const shape = node.querySelector<SVGElement>("rect, circle, ellipse, polygon, path");
      if (selectedText === text && shape) {
        shape.setAttribute("data-lets-selected", "1");
      } else if (shape) {
        shape.removeAttribute("data-lets-selected");
      }
    });

    return () => {
      cleanups.forEach((fn) => fn());
    };
  }, [selectedText, onSelect, votedTextsByDir]);

  // Inject per-node vote badges as <foreignObject> overlays. We re-run on
  // each render so when the user votes the badge updates.
  useEffect(() => {
    const root = ref.current;
    if (!root) return;
    const svg = root.querySelector("svg");
    if (!svg) return;
    // Remove any previous badges first so toggling doesn't double-render.
    svg.querySelectorAll("g[data-lets-badge]").forEach((el) => el.remove());

    const ns = "http://www.w3.org/2000/svg";
    const nodes = svg.querySelectorAll<SVGGElement>(
      "g.node, g.mindmap-node, g[class*='mindmap-node']",
    );
    nodes.forEach((node) => {
      const text = (node.textContent || "").trim();
      if (!text) return;
      const score = votedTextsByDir.get(text);
      if (!score) return;
      const shape = node.querySelector<SVGGraphicsElement>(
        "rect, circle, ellipse, polygon",
      );
      if (!shape) return;
      const bbox = shape.getBBox();
      const g = document.createElementNS(ns, "g");
      g.setAttribute("data-lets-badge", "1");
      const tx = bbox.x + bbox.width - 4;
      const ty = bbox.y - 6;
      const circle = document.createElementNS(ns, "circle");
      circle.setAttribute("cx", String(tx));
      circle.setAttribute("cy", String(ty));
      circle.setAttribute("r", "9");
      circle.setAttribute(
        "fill",
        score > 0 ? "var(--color-finding-bg)" : "var(--color-accent-soft)",
      );
      circle.setAttribute(
        "stroke",
        score > 0 ? "var(--color-finding)" : "var(--color-accent-border)",
      );
      circle.setAttribute("stroke-width", "1.2");
      const label = document.createElementNS(ns, "text");
      label.setAttribute("x", String(tx));
      label.setAttribute("y", String(ty + 3));
      label.setAttribute("text-anchor", "middle");
      label.setAttribute("font-size", "10");
      label.setAttribute("font-family", "monospace");
      label.setAttribute(
        "fill",
        score > 0 ? "var(--color-finding)" : "var(--color-accent-text)",
      );
      label.textContent = score > 0 ? `+${score}` : String(score);
      g.appendChild(circle);
      g.appendChild(label);
      node.appendChild(g);
    });
  }, [votedTextsByDir]);

  if (error) {
    return (
      <div className="my-2 border border-finding rounded p-2 text-[12px] text-finding font-mono">
        mermaid 渲染失败：{error.split("\n")[0]}
        <pre className="mt-1 text-text whitespace-pre-wrap">{source}</pre>
      </div>
    );
  }

  return <div ref={ref} aria-label="interactive diagram" className="relative" />;
}

export function getNodeTextsFromSource(source: string): string[] {
  // Best-effort: extract probable node labels from common mermaid syntaxes.
  // Not exhaustive — we mainly use SVG scanning at render time. This helper
  // exists so the feedback panel can pre-list nodes if needed.
  const out = new Set<string>();
  // graph TD / flowchart: `A[label]`, `A(label)`, `A{label}`
  for (const m of source.matchAll(/[A-Za-z0-9_]+\s*[\[\(\{]([^\]\)\}]+)[\]\)\}]/g)) {
    if (m[1]) out.add(m[1].trim());
  }
  // mindmap: indented `Root`, `  Child`, etc. — first significant text.
  for (const line of source.split("\n")) {
    const t = line.trim();
    if (!t) continue;
    if (t.startsWith("mindmap") || t.startsWith("graph") || t.startsWith("flowchart")) continue;
    const cleaned = t.replace(/^\(\(/, "").replace(/\)\)$/, "")
      .replace(/^\[\[/, "").replace(/\]\]$/, "")
      .replace(/^\[/, "").replace(/\]$/, "")
      .replace(/^\(/, "").replace(/\)$/, "")
      .trim();
    if (cleaned && cleaned.length < 80) out.add(cleaned);
  }
  return [...out];
}
