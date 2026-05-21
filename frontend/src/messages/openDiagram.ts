/**
 * Window-event bridge for opening a diagram in the side-sheet overlay.
 * Used by MermaidBlock (inline) and ReferencesPanel (right-pane chip) so
 * the overlay component itself can live above the rest of the layout
 * without those callers needing to know where it's mounted.
 *
 * Caller: openDiagram({ source, fromMsgId, label })
 * Sheet:  subscribeOpenDiagram(handler)
 */

const EVENT = "lets:open-diagram";

export interface OpenDiagramDetail {
  source: string;
  fromMsgId: number;
  label?: string;
  /** Topic id — needed so the overlay can post node-level annotations. */
  topicId?: number;
}

export function openDiagram(detail: OpenDiagramDetail): void {
  window.dispatchEvent(new CustomEvent(EVENT, { detail }));
}

export function subscribeOpenDiagram(
  handler: (detail: OpenDiagramDetail) => void,
): () => void {
  const listener = (e: Event) => {
    const d = (e as CustomEvent).detail as OpenDiagramDetail | undefined;
    if (d && typeof d.source === "string" && typeof d.fromMsgId === "number") {
      handler(d);
    }
  };
  window.addEventListener(EVENT, listener);
  return () => window.removeEventListener(EVENT, listener);
}
