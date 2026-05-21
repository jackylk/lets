import { useEffect, useMemo, useState } from "react";
import { InteractiveDiagram } from "./InteractiveDiagram";
import { NodeFeedbackPanel, useNodeAnnotations } from "./NodeFeedbackPanel";
import { subscribeOpenDiagram, type OpenDiagramDetail } from "./openDiagram";
import { jumpToMessage } from "../context/jumpToMessage";

interface Selected {
  text: string;
  cx: number;
  cy: number;
}

/**
 * Side-sheet that slides in from the right to host a full-size diagram.
 * Sits ABOVE the right pane but leaves the chat column on the left fully
 * interactive — the human can keep reading / typing while the diagram is
 * open. Inside, each node is clickable: selecting one opens the
 * `NodeFeedbackPanel` for +1/-1 votes and free-form annotations.
 *
 * Lifecycle:
 *   - Mounted once at TopicView level
 *   - Listens on window event "lets:open-diagram"
 *   - Close: Esc, × button, or 「跳回原消息」(which also triggers jumpToMessage)
 */
export function DiagramOverlay() {
  const [current, setCurrent] = useState<OpenDiagramDetail | null>(null);
  const [selected, setSelected] = useState<Selected | null>(null);

  useEffect(() => subscribeOpenDiagram((d) => {
    setCurrent(d);
    setSelected(null);
  }), []);

  useEffect(() => {
    if (!current) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setCurrent(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [current]);

  // Pull aggregate vote totals so the InteractiveDiagram can render per-node
  // badges as foreignObjects on the SVG. Only when we have a topicId
  // (annotations need a topic context).
  const hasContext = current?.topicId != null;

  return (
    <>
      {current && (
        <aside
          role="dialog"
          aria-label="diagram preview"
          className="fixed top-0 right-0 bottom-0 z-40 w-[min(70vw,860px)] bg-bg border-l border-border shadow-[-12px_0_30px_-12px_rgba(0,0,0,0.15)] flex flex-col animate-slide-in-right"
        >
          <header className="flex items-center justify-between px-4 h-[42px] border-b border-border-soft shrink-0">
            <div className="text-[12px] font-mono uppercase tracking-[0.06em] text-text-dim">
              {current.label || "diagram"}
            </div>
            <div className="flex items-center gap-3 text-[11.5px]">
              <button
                type="button"
                onClick={() => {
                  jumpToMessage(current.fromMsgId);
                  setCurrent(null);
                }}
                className="text-text-dim hover:text-accent-text underline-offset-2 hover:underline"
                title="关闭预览并跳到聊天里这张图所在的消息"
              >
                跳回原消息
              </button>
              <button
                type="button"
                onClick={() => setCurrent(null)}
                className="font-mono text-text-dim hover:text-text px-1"
                title="关闭 (Esc)"
                aria-label="close"
              >
                ×
              </button>
            </div>
          </header>
          <div className="flex-1 overflow-auto p-5 flex flex-col gap-3">
            {hasContext ? (
              <DiagramWithFeedback
                detail={current}
                selected={selected}
                onSelect={setSelected}
              />
            ) : (
              // Fallback: no topicId means we can't post annotations; just
              // render the diagram without interactivity.
              <div className="border border-border-soft rounded bg-surface-elev px-3 py-3">
                <InteractiveDiagram
                  source={current.source}
                  onSelect={() => {}}
                  selectedText={null}
                  votedTextsByDir={new Map()}
                />
              </div>
            )}
          </div>
        </aside>
      )}
    </>
  );
}

function DiagramWithFeedback({
  detail,
  selected,
  onSelect,
}: {
  detail: OpenDiagramDetail;
  selected: Selected | null;
  onSelect: (s: Selected | null) => void;
}) {
  const topicId = detail.topicId as number;
  const { scoreByNode } = useNodeAnnotations(topicId, detail.fromMsgId);

  const votedTextsByDir = useMemo(() => new Map(scoreByNode), [scoreByNode]);

  return (
    <>
      <div className="border border-border-soft rounded bg-surface-elev px-3 py-3 relative">
        <InteractiveDiagram
          source={detail.source}
          onSelect={onSelect}
          selectedText={selected?.text ?? null}
          votedTextsByDir={votedTextsByDir}
        />
        {/* Selection marker pin — small dot at the clicked node center */}
        {selected && (
          <span
            aria-hidden
            className="absolute pointer-events-none w-2.5 h-2.5 rounded-full border-2 border-accent bg-bg"
            style={{
              left: selected.cx - 5,
              top: selected.cy - 5,
            }}
          />
        )}
      </div>
      <NodeFeedbackPanel
        topicId={topicId}
        diagramMsgId={detail.fromMsgId}
        selectedNode={selected?.text ?? null}
      />
    </>
  );
}
