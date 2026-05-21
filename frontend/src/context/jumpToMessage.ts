/**
 * Bridge between right-pane cards and chat-stream highlight, used because
 * the right pane is rendered outside TopicView's StreamProvider (they're
 * siblings in AppShell). Dispatching a window event keeps both sides
 * loosely coupled and avoids hoisting StreamProvider up to App.
 *
 * Right pane: call jumpToMessage(msgId) when a card is clicked.
 * Stream side: listen for "lets:jump" via subscribeJumpToMessage and on
 *   each event scrollIntoView the matching message + flash highlight it
 *   via the existing StreamContext.setHighlighted/clearHighlight.
 */

const EVENT = "lets:jump";

export function jumpToMessage(msgId: number): void {
  window.dispatchEvent(new CustomEvent(EVENT, { detail: { msgId } }));
}

export function subscribeJumpToMessage(handler: (msgId: number) => void): () => void {
  const listener = (e: Event) => {
    const id = (e as CustomEvent).detail?.msgId;
    if (typeof id === "number") handler(id);
  };
  window.addEventListener(EVENT, listener);
  return () => window.removeEventListener(EVENT, listener);
}
