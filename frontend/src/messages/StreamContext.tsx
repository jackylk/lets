import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { MessageDTO } from "../api/types";
import type { Directory } from "./actorResolver";
import { makeActorResolver } from "./actorResolver";

export type ViewMode = "full" | "collapsed" | "humans-only";

interface StreamCtx {
  byId: Map<number, MessageDTO>;
  resolveActor: ReturnType<typeof makeActorResolver>;
  /** Message IDs the user is asking us to highlight (cited by a hovered provenance row). */
  highlighted: Set<number>;
  setHighlighted: (ids: number[]) => void;
  clearHighlight: () => void;
  /**
   * Highest message id any agent has acknowledged reading (max of all
   * `metadata.cites` across agent chats). 0 means no agent reply yet — UI
   * suppresses the read cursor entirely in that case.
   */
  readCursor: number;
  /** Global view mode for agent messages. Persisted per-topic. */
  viewMode: ViewMode;
  setViewMode: (m: ViewMode) => void;
  /** Per-message manual overrides — "expanded" beats the global collapsed mode. */
  isExpanded: (msgId: number) => boolean;
  toggleExpanded: (msgId: number) => void;
}

const empty: StreamCtx = {
  byId: new Map(),
  resolveActor: makeActorResolver({ humans: [], agentInstances: [] }),
  highlighted: new Set(),
  setHighlighted: () => {},
  clearHighlight: () => {},
  readCursor: 0,
  viewMode: "collapsed",
  setViewMode: () => {},
  isExpanded: () => false,
  toggleExpanded: () => {},
};

const Ctx = createContext<StreamCtx>(empty);

interface ProviderProps {
  messages: MessageDTO[];
  directory: Directory;
  /** Topic id is the localStorage scope key for viewMode. */
  topicId: number;
  children: ReactNode;
}

const VIEW_MODE_KEY_PREFIX = "lets:view-mode:topic:";

function loadViewMode(topicId: number): ViewMode {
  try {
    const v = window.localStorage.getItem(VIEW_MODE_KEY_PREFIX + topicId);
    if (v === "full" || v === "collapsed" || v === "humans-only") return v;
  } catch { /* ignore */ }
  return "collapsed";  // per Codex's recommendation
}

export function StreamProvider({ messages, directory, topicId, children }: ProviderProps) {
  const [highlighted, setHighlightedSet] = useState<Set<number>>(() => new Set());
  const [viewMode, setViewModeState] = useState<ViewMode>(() => loadViewMode(topicId));
  const [expandedIds, setExpandedIds] = useState<Set<number>>(() => new Set());

  // Switching topics resets the per-message override + reloads view mode.
  useEffect(() => {
    setExpandedIds(new Set());
    setViewModeState(loadViewMode(topicId));
  }, [topicId]);

  const setViewMode = useCallback((m: ViewMode) => {
    setViewModeState(m);
    setExpandedIds(new Set());  // a new view mode clears per-message overrides
    try {
      window.localStorage.setItem(VIEW_MODE_KEY_PREFIX + topicId, m);
    } catch { /* ignore */ }
  }, [topicId]);

  const toggleExpanded = useCallback((msgId: number) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(msgId)) next.delete(msgId);
      else next.add(msgId);
      return next;
    });
  }, []);

  const value = useMemo<StreamCtx>(() => {
    let readCursor = 0;
    for (const m of messages) {
      if (m.actor_type !== "agent" || m.type !== "chat") continue;
      const cites = (m.metadata as Record<string, unknown> | null)?.cites;
      if (!Array.isArray(cites)) continue;
      for (const c of cites) {
        if (typeof c === "number" && c > readCursor) readCursor = c;
      }
    }
    return {
      byId: new Map(messages.map((m) => [m.id, m])),
      resolveActor: makeActorResolver(directory),
      highlighted,
      setHighlighted: (ids) => setHighlightedSet(new Set(ids)),
      clearHighlight: () => setHighlightedSet(new Set()),
      readCursor,
      viewMode,
      setViewMode,
      isExpanded: (id: number) => expandedIds.has(id),
      toggleExpanded,
    };
  }, [messages, directory, highlighted, viewMode, expandedIds, setViewMode, toggleExpanded]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useStream() {
  return useContext(Ctx);
}
