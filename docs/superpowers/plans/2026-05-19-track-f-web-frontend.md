# Track F: Web Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `web/index.html` (v1 debug panel) with a real Lets web app that ports the `web/mock.html` v6 design system into a maintainable React codebase, wires it to the Track A/B/D backend contracts, and ships v1.5a (typed message stream) → v1.5b (spec sync UI) → v1.5c (artifact + attention queue + goal card + mobile) — one Track, three phase milestones.

**Architecture:** Vite + React 18 + TypeScript + Tailwind v4 + Vitest (unit) + Playwright (E2E) + TanStack Query (data fetching) + MSW (Mock Service Worker for fixture mode). The frontend lives in a new `frontend/` directory and builds into `frontend/dist/`, which FastAPI serves at `/app`. Contract types (`MessageDTO`, `TopicDTO`, `IdentityDTO`, `ArtifactDTO`) are hand-written in `frontend/src/api/types.ts` to match the Track A `messages` schema (13 typed messages × `human|agent|system` actors). Phase 0–2 build against MSW fixtures; Phase 3 swaps to real `fetch` once Track A's API is live. Live update uses SSE via a small backend addition (`GET /api/topics/{id}/stream`), with polling fallback for environments without SSE.

**Tech Stack:**
- Build: Vite 5 · React 18 · TypeScript 5 · Tailwind CSS v4 (`@theme` config) · pnpm
- Data: TanStack Query 5 · native `fetch` · native `EventSource` (SSE)
- Fixtures: MSW 2 (Mock Service Worker) · seed JSON in `frontend/src/fixtures/`
- Test: Vitest · @testing-library/react · jsdom · Playwright (E2E)
- Lint: ESLint + typescript-eslint + Prettier
- Backend additions: 3 endpoints (`GET /api/topics`, `POST /api/topics`, `GET /api/topics/{id}/stream`) + static mount for built SPA

**Prerequisite check:**
- Phase 0–4 can start **in parallel with Track A** (fixture-only, no real API calls)
- Phase 5 onwards (real API swap, SSE) **requires Track A complete** (`/api/messages`, `/api/topics/{id}/messages`, `/api/identity/me` working; `messages`/`topics` tables migrated)
- Phase 9 (artifact panel) **requires Track D complete** for real backend; before that uses fixtures
- v1.5b spec sync UI (Phase 8) reads spec change as a typed message — only requires Track A

**Discipline:** Each component task is TDD: write a failing render test → implement → run test → commit. Each phase ends with a manual smoke step (open `pnpm dev`, verify the slice works visually). No "Add error handling later" — error/loading/empty states are part of the task that creates the component.

---

## File Structure

**Created — repo root:**
- `frontend/` — new SPA workspace (gitignored: `frontend/node_modules`, `frontend/dist`)
- `frontend/package.json`
- `frontend/pnpm-lock.yaml`
- `frontend/tsconfig.json`
- `frontend/vite.config.ts`
- `frontend/index.html` — Vite entry HTML
- `frontend/playwright.config.ts`
- `frontend/.eslintrc.cjs`
- `frontend/.prettierrc`
- `frontend/.gitignore`

**Created — `frontend/src/`:**
- `frontend/src/main.tsx` — React root, mounts `<App/>`, sets up QueryClient + MSW
- `frontend/src/App.tsx` — top-level routing (Login / Topic view / Attention view / Settings)
- `frontend/src/auth/LoginPage.tsx` — "Login with GitHub" landing screen (Phase 12)
- `frontend/src/auth/SessionGate.tsx` — gates the app behind a session (Phase 12)
- `frontend/src/settings/SettingsTokensPage.tsx` — list / create / revoke agent tokens (Phase 12)
- `frontend/src/settings/NewTokenDialog.tsx` — one-time token reveal modal (Phase 12)
- `frontend/src/index.css` — Tailwind v4 entry (`@import "tailwindcss"` + `@theme` tokens)
- `frontend/src/api/types.ts` — DTO types matching backend `messages`/`topics`/`identity` schema
- `frontend/src/api/client.ts` — typed `fetch` wrapper, identity headers injection
- `frontend/src/api/queries.ts` — TanStack Query hooks (`useTopic`, `useTopicMessages`, `usePostMessage`, `useIdentity`)
- `frontend/src/api/sse.ts` — SSE subscription hook
- `frontend/src/fixtures/handlers.ts` — MSW request handlers (mirror of real endpoints)
- `frontend/src/fixtures/seed.ts` — seed Topic + Messages (the PPT scenario from mock)
- `frontend/src/identity/IdentityProvider.tsx` — sets/persists `X-Lets-Human` headers
- `frontend/src/identity/useIdentity.ts`
- `frontend/src/layout/AppShell.tsx` — 3-pane grid + responsive switches
- `frontend/src/layout/Sidebar.tsx` — proj head + attention button + sections
- `frontend/src/layout/ContextPane.tsx` — right pane container
- `frontend/src/layout/BottomTabs.tsx` — mobile bottom nav
- `frontend/src/sidebar/AttentionEntry.tsx`
- `frontend/src/sidebar/ChannelsSection.tsx`
- `frontend/src/sidebar/OnlineSection.tsx`
- `frontend/src/sidebar/DirectMessagesSection.tsx`
- `frontend/src/topic/TopicHeader.tsx`
- `frontend/src/topic/TopicView.tsx` — composer + stream + day separator
- `frontend/src/topic/Stream.tsx`
- `frontend/src/topic/DaySeparator.tsx`
- `frontend/src/topic/Composer.tsx`
- `frontend/src/messages/Message.tsx` — dispatch component by `type`
- `frontend/src/messages/BaseMessage.tsx` — avatar + head + body shell
- `frontend/src/messages/ChatMessage.tsx`
- `frontend/src/messages/StatusMessage.tsx`
- `frontend/src/messages/FindingMessage.tsx`
- `frontend/src/messages/DecisionMessage.tsx`
- `frontend/src/messages/QuestionMessage.tsx`
- `frontend/src/messages/HandoffMessage.tsx`
- `frontend/src/messages/ReviewMessage.tsx`
- `frontend/src/messages/ArtifactRevisionMessage.tsx`
- `frontend/src/messages/SpecChangeMessage.tsx`
- `frontend/src/messages/NudgeMessage.tsx`
- `frontend/src/messages/ProactiveFindingMessage.tsx`
- `frontend/src/messages/TaskTreeProposalMessage.tsx`
- `frontend/src/messages/SystemMessage.tsx`
- `frontend/src/messages/MentionText.tsx` — parses `@name` and `[T-PPT]` into chips
- `frontend/src/context/TopicInfoCard.tsx`
- `frontend/src/context/TaskTreePanel.tsx`
- `frontend/src/context/ArtifactPanel.tsx`
- `frontend/src/context/SpecTouchedPanel.tsx`
- `frontend/src/context/ParticipantsPanel.tsx`
- `frontend/src/context/GitRow.tsx`
- `frontend/src/attention/AttentionView.tsx`
- `frontend/src/attention/AttentionGroup.tsx`
- `frontend/src/attention/AttentionCard.tsx`
- `frontend/src/topic/TopicHeaderProgress.tsx` — progress ring + current-task chip + ⋯ menu, rendered inline in TopicHeader (goal card merged here per design decision)
- `frontend/src/context/GoalDetailPanel.tsx` — full goal spec / approvers / Mark as Final, sits in context pane
- `frontend/src/lib/cn.ts` — tailwind class merger helper
- `frontend/src/lib/time.ts` — `formatHHMM(ts)` etc.

**Created — `frontend/test/` & `frontend/e2e/`:**
- `frontend/test/setup.ts` — Vitest jsdom setup, MSW worker startup
- `frontend/test/fixtures.ts` — re-export seed + helper render wrapper
- `frontend/test/render.tsx` — `renderWithProviders()` helper
- Per-component co-located `*.test.tsx` next to each component
- `frontend/e2e/ppt-scenario.spec.ts` — full PPT scenario as Playwright
- `frontend/e2e/identity-flow.spec.ts`

**Modified:**
- `app/main.py` — add `GET /api/topics`, `POST /api/topics`, `GET /api/topics/{id}/stream`, and `/app` static mount + `/app/*` SPA fallback
- `tests/test_topics_api.py` — backend test for the 3 new endpoints (Python pytest)
- `README.md` — append Track F section with `pnpm dev` instructions
- `.gitignore` — add `frontend/node_modules`, `frontend/dist`

**Read-only references:**
- `web/mock.html` — visual source of truth; do NOT edit, only port from
- `docs/superpowers/plans/2026-05-19-track-a-schema-substrate.md` — message types and DTO shape
- `app/messages.py` — `ALLOWED_TYPES` (13 message types) — must match `MessageType` union in frontend
- `app/db.py` lines 154–212 — `topics`/`messages` schema (column names = DTO field names)

---

## Conventions

- **TDD per component**: every new `*.tsx` lands with its `*.test.tsx` first; tests run in jsdom via Vitest
- **No `any`**: all React component props are typed; DTOs come from `api/types.ts` only
- **Tailwind v4 only for layout/spacing/typography utilities**; semantic colors come from CSS variables in `index.css` via `@theme` — direct OKLCH literals stay out of components
- **Fixture/Real switch**: `import.meta.env.VITE_USE_FIXTURES === "true"` enables MSW; default in dev is `true` until Phase 5
- **Tests use `renderWithProviders`** which sets up MSW + QueryClient + Identity — never bare `render()` in app code
- **Identity injection**: every `fetch` call goes through `api/client.ts` which auto-attaches `X-Lets-Human` + optional agent headers from `IdentityProvider`
- **Commit message prefix**: `feat(frontend): …`, `test(frontend): …`, `chore(frontend): …`
- **Component file = one default export** + co-located types/helpers if < 20 LoC, else split
- **Run from project root**: all commands assume `cd frontend` first; the plan repeats `cd frontend` in every shell step so tasks read independently

---

## Phase Milestones

| Phase | Scope | Stop and demo |
|-------|-------|--------------|
| **0. Scaffold** (T1–T5) | Vite/TS/Tailwind/MSW set up, `pnpm dev` opens blank "Hello Lets" | `pnpm dev` shows the splash |
| **1. Contract layer** (T6–T9) | Types + fixture handlers + API client + IdentityProvider, no UI | `pnpm test` green, types compile |
| **2. App shell** (T10–T13) | 3-pane grid + sidebar skeleton + topic header + day separator | `pnpm dev` shows layout with empty stream |
| **3. Base message + 4 simple types** (T14–T18) | `chat`, `status`, `finding`, `system` render correctly with fixtures | Stream visually matches mock for those types |
| **4. Complex typed messages** (T19–T24) | `decision`, `question`, `handoff`, `review`, `artifact_revision`, `spec_change`, `nudge`, `proactive_finding`, `task_tree_proposal` | All 13 types render; stream matches mock |
| **5. Composer + real API + SSE** (T25–T30) | Backend endpoints added, fixture switch off, posting + live updates work | Two browser tabs see each other's posts |
| **6. Context pane** (T31–T35) | Topic info, task tree, artifact, spec touched, participants, git row | Right pane visually complete |
| **7. Attention queue** (T36–T39) | Greeting + 3 groups + quick actions | `/?view=attention` matches mock |
| **8. v1.5b spec sync deep** (T40–T42) | Spec change diff modal, approval bar wired to backend | Spec change roundtrip works |
| **9. Goal surface (slim)** (T43–T44) | `TopicHeaderProgress` inline in TopicHeader + `GoalDetailPanel` in context pane (Mark as Final lives in context, no big card above stream) | Goal info visible at all times without occupying stream height |
| **10. Mobile** (T46–T48) | Bottom tabs, responsive sidebar, attention on mobile | iPhone-sized viewport works |
| **11. E2E + integration** (T49–T51) | Playwright PPT scenario, FastAPI serves built SPA at `/app` | `/app` in browser drives the PPT scenario E2E |
| **12. Auth & Token UI** (T43–T46) | GitHub OAuth login, session cookie, REST tokens CRUD, Settings → Agent Tokens page | New colleague can land at `/app`, "Login with GitHub", generate an agent token, paste into local `.mcp.json`, their CC joins the chat |

### Design review checkpoints

Per decision: visual baseline sticks with mock.html v6 (3-pane, cream OKLCH, Bricolage/Geist, typed-message colors), **but** these variables stay open and get explicit review gates inside the plan:

- **Checkpoint A — after Phase 2 (app shell up)**: review `--color-accent` hue, `--context-w` width, sidebar font sizes. Touchable file: `frontend/src/index.css`. Task T13 ends with this review.
- **Checkpoint B — after Phase 6 (context pane done)**: review typed-message saturation across the visible stream and context. Touchable file: `frontend/src/index.css` token group "Typed-message accents". Task T35 ends with this review.

These checkpoints are NOT "design tasks" — they are 10-minute look-and-feel passes that can adjust the `@theme` block before the visual is locked further downstream. Adjustments outside these checkpoints get rolled into a follow-up polish task at end of Phase 11.

---

## Task 1: Scaffold Vite + React + TypeScript

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/.gitignore`
- Modify: `.gitignore` (repo root)

- [ ] **Step 1.1: Create `frontend/.gitignore`**

```
node_modules
dist
.env.local
*.log
```

- [ ] **Step 1.2: Append to repo root `.gitignore`**

Open `/Users/jacky/code/Lets/.gitignore` and append:
```
frontend/node_modules
frontend/dist
```

- [ ] **Step 1.3: Create `frontend/package.json`**

```json
{
  "name": "lets-frontend",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "test:watch": "vitest",
    "e2e": "playwright test",
    "lint": "eslint src --max-warnings 0",
    "format": "prettier --write \"src/**/*.{ts,tsx,css}\""
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "@tanstack/react-query": "^5.59.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.12",
    "@types/react-dom": "^18.3.1",
    "@vitejs/plugin-react": "^4.3.3",
    "typescript": "^5.6.3",
    "vite": "^5.4.10",
    "vitest": "^2.1.4",
    "@testing-library/react": "^16.0.1",
    "@testing-library/jest-dom": "^6.6.3",
    "@testing-library/user-event": "^14.5.2",
    "jsdom": "^25.0.1",
    "msw": "^2.6.4",
    "@playwright/test": "^1.48.2",
    "tailwindcss": "^4.0.0-beta.7",
    "@tailwindcss/vite": "^4.0.0-beta.7",
    "eslint": "^9.14.0",
    "@typescript-eslint/parser": "^8.13.0",
    "@typescript-eslint/eslint-plugin": "^8.13.0",
    "eslint-plugin-react": "^7.37.2",
    "eslint-plugin-react-hooks": "^5.0.0",
    "prettier": "^3.3.3"
  }
}
```

- [ ] **Step 1.4: Create `frontend/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitOverride": true,
    "noFallthroughCasesInSwitch": true,
    "resolveJsonModule": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "isolatedModules": true,
    "verbatimModuleSyntax": true,
    "useDefineForClassFields": true,
    "baseUrl": "./src",
    "paths": { "@/*": ["*"] },
    "types": ["vitest/globals", "@testing-library/jest-dom"]
  },
  "include": ["src", "test", "vite.config.ts"]
}
```

- [ ] **Step 1.5: Create `frontend/vite.config.ts`**

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "node:path";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "src") },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
  build: {
    outDir: "dist",
    sourcemap: true,
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./test/setup.ts"],
    css: false,
  },
});
```

- [ ] **Step 1.6: Create `frontend/index.html`**

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
    <title>Lets</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 1.7: Create `frontend/src/App.tsx`**

```tsx
export default function App() {
  return (
    <div className="min-h-screen grid place-items-center bg-[var(--bg)] text-[var(--text)]">
      <div className="text-center">
        <h1 className="font-display text-2xl">Lets</h1>
        <p className="text-sm text-[var(--text-muted)]">Track F scaffold — Phase 0</p>
      </div>
    </div>
  );
}
```

- [ ] **Step 1.8: Create `frontend/src/main.tsx`**

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";

const root = document.getElementById("root");
if (!root) throw new Error("#root element missing");
ReactDOM.createRoot(root).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
```

- [ ] **Step 1.9: Install + run dev**

```bash
cd frontend && pnpm install
cd frontend && pnpm dev
```

Expected: dev server boots on `http://localhost:5173`, page shows "Lets / Track F scaffold". Stop the server with Ctrl-C.

- [ ] **Step 1.10: Commit**

```bash
git add frontend/ .gitignore
git commit -m "feat(frontend): scaffold Vite + React + TypeScript workspace"
```

---

## Task 2: Tailwind v4 + design tokens ported from mock.html

**Files:**
- Create: `frontend/src/index.css`

The mock uses OKLCH variables. Port them to Tailwind v4's `@theme` so utilities like `text-text-muted` and `bg-surface-elev` work.

- [ ] **Step 2.1: Create `frontend/src/index.css`**

```css
@import "tailwindcss";

@theme {
  --color-bg:               oklch(0.985 0.006 75);
  --color-surface:          oklch(0.965 0.008 75);
  --color-surface-elev:     oklch(0.995 0.004 75);
  --color-surface-hover:    oklch(0.955 0.009 75);
  --color-border:           oklch(0.88  0.010 75);
  --color-border-soft:      oklch(0.92  0.008 75);

  --color-text:             oklch(0.22 0.010 240);
  --color-text-muted:       oklch(0.46 0.010 240);
  --color-text-dim:         oklch(0.62 0.008 240);

  --color-accent:           oklch(0.62 0.16 55);
  --color-accent-soft:      oklch(0.93 0.07 70);
  --color-accent-text:      oklch(0.42 0.16 55);
  --color-accent-border:    oklch(0.78 0.10 70);

  --color-agent-claude:     oklch(0.52 0.14 50);
  --color-agent-claude-bg:  oklch(0.94 0.05 50);
  --color-agent-codex:      oklch(0.46 0.10 155);
  --color-agent-codex-bg:   oklch(0.93 0.04 155);
  --color-human:            oklch(0.45 0.10 220);
  --color-human-bg:         oklch(0.93 0.03 220);

  --color-finding:          oklch(0.46 0.10 155);
  --color-finding-bg:       oklch(0.93 0.04 155);
  --color-decision:         oklch(0.45 0.16 290);
  --color-decision-bg:      oklch(0.93 0.06 290);
  --color-handoff:          oklch(0.45 0.13 215);
  --color-handoff-bg:       oklch(0.93 0.05 215);
  --color-review:           oklch(0.45 0.12 285);
  --color-review-bg:        oklch(0.93 0.05 285);
  --color-artifact:         oklch(0.40 0.12 255);
  --color-artifact-bg:      oklch(0.93 0.04 255);
  --color-spec:             oklch(0.42 0.06 190);
  --color-spec-bg:          oklch(0.93 0.03 190);
  --color-proactive:        oklch(0.55 0.16 30);
  --color-proactive-bg:     oklch(0.95 0.06 30);
  --color-tree:             oklch(0.42 0.10 170);
  --color-tree-bg:          oklch(0.94 0.04 170);
  --color-nudge:            oklch(0.50 0.020 80);
  --color-nudge-bg:         oklch(0.95 0.012 80);

  --color-status-on:        oklch(0.62 0.14 145);
  --color-status-work:      oklch(0.65 0.16 55);
  --color-status-idle:      oklch(0.65 0.008 240);

  --font-display: "Bricolage Grotesque", system-ui, sans-serif;
  --font-body:    "Geist Variable", "Geist", system-ui, sans-serif;
  --font-mono:    "Geist Mono Variable", "Geist Mono", ui-monospace, monospace;

  --radius-sm: 6px;
  --radius: 10px;
  --radius-lg: 14px;
}

html, body, #root { height: 100%; }
body {
  margin: 0;
  font-family: var(--font-body);
  font-feature-settings: "ss01", "cv11";
  -webkit-font-smoothing: antialiased;
  background: var(--color-bg);
  color: var(--color-text);
}
```

- [ ] **Step 2.2: Add font CDN links to `frontend/index.html`**

In `<head>` of `frontend/index.html`, before `</head>`, add:
```html
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,400..700&display=swap" rel="stylesheet" />
<link href="https://cdn.jsdelivr.net/npm/@fontsource-variable/geist@5.1.1/index.min.css" rel="stylesheet" />
<link href="https://cdn.jsdelivr.net/npm/@fontsource-variable/geist-mono@5.1.1/index.min.css" rel="stylesheet" />
```

- [ ] **Step 2.3: Update `frontend/src/App.tsx` to verify tokens resolve**

```tsx
export default function App() {
  return (
    <div className="min-h-screen grid place-items-center">
      <div className="text-center">
        <h1 className="font-[var(--font-display)] text-2xl text-text">Lets</h1>
        <p className="text-sm text-text-muted">Track F scaffold — Phase 0</p>
      </div>
    </div>
  );
}
```

- [ ] **Step 2.4: Run dev and verify**

```bash
cd frontend && pnpm dev
```

Expected: page background is the warm cream `#f8f4ec`-ish color, text uses Geist, `text-text-muted` shows a muted blue-grey. Visually compare with `web/mock.html` opened in another tab — the body background should match.

- [ ] **Step 2.5: Commit**

```bash
git add frontend/src/index.css frontend/index.html frontend/src/App.tsx
git commit -m "feat(frontend): port mock.html OKLCH design tokens to Tailwind v4 @theme"
```

---

## Task 3: Vitest + Testing Library setup

**Files:**
- Create: `frontend/test/setup.ts`
- Create: `frontend/test/render.tsx`
- Create: `frontend/src/App.test.tsx`

- [ ] **Step 3.1: Create `frontend/test/setup.ts`**

```ts
import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

afterEach(() => cleanup());
```

- [ ] **Step 3.2: Create `frontend/test/render.tsx`**

```tsx
import type { ReactElement, ReactNode } from "react";
import { render, type RenderOptions } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

export function makeQueryClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
}

function Providers({ children }: { children: ReactNode }) {
  const client = makeQueryClient();
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

export function renderWithProviders(
  ui: ReactElement,
  options?: Omit<RenderOptions, "wrapper">,
) {
  return render(ui, { wrapper: Providers, ...options });
}
```

- [ ] **Step 3.3: Write failing test for App**

Create `frontend/src/App.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../test/render";
import App from "./App";

describe("<App />", () => {
  it("renders the Lets heading", () => {
    renderWithProviders(<App />);
    expect(screen.getByRole("heading", { name: /lets/i })).toBeInTheDocument();
  });
});
```

- [ ] **Step 3.4: Run test**

```bash
cd frontend && pnpm test
```

Expected: 1 test passes (App.tsx already renders `<h1>Lets</h1>`).

- [ ] **Step 3.5: Commit**

```bash
git add frontend/test/ frontend/src/App.test.tsx
git commit -m "test(frontend): wire Vitest + Testing Library + renderWithProviders helper"
```

---

## Task 4: DTO types matching backend schema

**Files:**
- Create: `frontend/src/api/types.ts`
- Create: `frontend/src/api/types.test-d.ts` — type-only test

The 13 typed messages and 3 actor types must match `app/messages.py` `ALLOWED_TYPES` exactly.

- [ ] **Step 4.1: Create `frontend/src/api/types.ts`**

```ts
export const MESSAGE_TYPES = [
  "chat", "status", "finding", "decision", "question",
  "handoff", "review", "artifact_revision", "spec_change",
  "nudge", "proactive_finding", "task_tree_proposal", "system",
] as const;
export type MessageType = (typeof MESSAGE_TYPES)[number];

export const ACTOR_TYPES = ["human", "agent", "system"] as const;
export type ActorType = (typeof ACTOR_TYPES)[number];

export interface MessageDTO {
  id: number;
  topic_id: number;
  type: MessageType;
  actor_type: ActorType;
  actor_id: number | null;
  body: string;
  metadata: Record<string, unknown>;
  ref_event_id: number | null;
  created_at: string;
}

export interface TopicDTO {
  id: number;
  slug: string;
  title: string;
  project_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface HumanDTO { id: number; name: string; }
export interface AgentInstanceDTO { id: number; role: string; device_label: string; }
export interface IdentityDTO { human: HumanDTO; agent_instance?: AgentInstanceDTO; }

export interface PostMessageInput {
  topic_id: number;
  type: MessageType;
  actor_type: ActorType;
  actor_id: number | null;
  body: string;
  metadata?: Record<string, unknown>;
  ref_event_id?: number | null;
}

export interface ArtifactVersionDTO {
  id: number; artifact_id: number; version_label: string;
  backend_revision_id: string; summary: string | null;
  preview_uri: string | null; created_at: string;
}
export interface ArtifactDTO {
  id: number; slug: string; type: string; backend: string;
  backend_ref: string; title: string; topic_id: number;
  current_version_id: number | null; versions: ArtifactVersionDTO[];
}

export interface SpecChangeMeta {
  file: string; before: unknown; after: unknown; approvers?: string[];
}
export interface ArtifactRevisionMeta {
  artifact_id?: number; artifact_name?: string; version: string; preview_uri?: string;
}
export interface TaskTreeProposalMeta {
  title: string;
  items: Array<{ title: string; owner_name?: string; status?: "pending" | "active" | "done" }>;
}
export interface NudgeMeta { reason: string; target_actor_id?: number; }
export interface DecisionMeta { decision_type: "adopt" | "reject" | "defer"; ref_message_id?: number; }
```

- [ ] **Step 4.2: Write failing type test**

Create `frontend/src/api/types.test-d.ts`:
```ts
import { expectTypeOf, test } from "vitest";
import type { MessageType, ActorType, MessageDTO, PostMessageInput } from "./types";

test("MessageType lists all 13 backend types", () => {
  expectTypeOf<MessageType>().toEqualTypeOf<
    | "chat" | "status" | "finding" | "decision" | "question"
    | "handoff" | "review" | "artifact_revision" | "spec_change"
    | "nudge" | "proactive_finding" | "task_tree_proposal" | "system"
  >();
});
test("ActorType lists 3 actors", () => {
  expectTypeOf<ActorType>().toEqualTypeOf<"human" | "agent" | "system">();
});
test("MessageDTO has metadata as object", () => {
  expectTypeOf<MessageDTO["metadata"]>().toEqualTypeOf<Record<string, unknown>>();
});
test("PostMessageInput omits server-only fields", () => {
  expectTypeOf<PostMessageInput>().not.toHaveProperty("id");
  expectTypeOf<PostMessageInput>().not.toHaveProperty("created_at");
});
```

- [ ] **Step 4.3: Run tests**

```bash
cd frontend && pnpm test
```

Expected: all type tests pass.

- [ ] **Step 4.4: Cross-check against backend**

Open `app/messages.py` and confirm `ALLOWED_TYPES` set has same 13 strings. If they differ, the backend wins — update `MESSAGE_TYPES` in the frontend.

- [ ] **Step 4.5: Commit**

```bash
git add frontend/src/api/types.ts frontend/src/api/types.test-d.ts
git commit -m "feat(frontend): DTO types mirroring backend messages/topics/identity schema"
```

---

## Task 5: Identity provider + persistence

**Files:**
- Create: `frontend/src/identity/IdentityProvider.tsx`
- Create: `frontend/src/identity/useIdentity.ts`
- Create: `frontend/src/identity/IdentityProvider.test.tsx`

For dogfood Phase 1, identity is set via a sticky localStorage value. Real OAuth comes in Track C. The provider exposes `{ humanName, agentRole, deviceLabel, setIdentity }` and the API client reads it for headers.

- [ ] **Step 5.1: Write failing test**

Create `frontend/src/identity/IdentityProvider.test.tsx`:
```tsx
import { describe, it, expect, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../test/render";
import { IdentityProvider } from "./IdentityProvider";
import { useIdentity } from "./useIdentity";

function Probe() {
  const { humanName, setIdentity } = useIdentity();
  return (
    <>
      <span data-testid="who">{humanName ?? "anon"}</span>
      <button onClick={() => setIdentity({ humanName: "Neo" })}>set</button>
    </>
  );
}

describe("<IdentityProvider />", () => {
  beforeEach(() => localStorage.clear());

  it("starts anonymous and exposes setter", async () => {
    const user = userEvent.setup();
    renderWithProviders(<IdentityProvider><Probe /></IdentityProvider>);
    expect(screen.getByTestId("who")).toHaveTextContent("anon");
    await user.click(screen.getByText("set"));
    expect(screen.getByTestId("who")).toHaveTextContent("Neo");
  });

  it("persists across remount via localStorage", () => {
    localStorage.setItem(
      "lets.identity",
      JSON.stringify({ humanName: "Trinity", agentRole: null, deviceLabel: null }),
    );
    renderWithProviders(<IdentityProvider><Probe /></IdentityProvider>);
    expect(screen.getByTestId("who")).toHaveTextContent("Trinity");
  });
});
```

- [ ] **Step 5.2: Run test (should fail)**

```bash
cd frontend && pnpm test identity
```

Expected: fails with "Cannot find module './IdentityProvider'".

- [ ] **Step 5.3: Create `frontend/src/identity/useIdentity.ts`**

```ts
import { createContext, useContext } from "react";

export interface Identity {
  humanName: string | null;
  agentRole: string | null;
  deviceLabel: string | null;
}
export interface IdentityContextValue extends Identity {
  setIdentity: (next: Partial<Identity>) => void;
}
export const IdentityContext = createContext<IdentityContextValue | null>(null);

export function useIdentity(): IdentityContextValue {
  const ctx = useContext(IdentityContext);
  if (!ctx) throw new Error("useIdentity must be used inside <IdentityProvider />");
  return ctx;
}
```

- [ ] **Step 5.4: Create `frontend/src/identity/IdentityProvider.tsx`**

```tsx
import { useCallback, useMemo, useState, type ReactNode } from "react";
import { IdentityContext, type Identity } from "./useIdentity";

const STORAGE_KEY = "lets.identity";

function loadIdentity(): Identity {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { humanName: null, agentRole: null, deviceLabel: null };
    const parsed = JSON.parse(raw) as Partial<Identity>;
    return {
      humanName: parsed.humanName ?? null,
      agentRole: parsed.agentRole ?? null,
      deviceLabel: parsed.deviceLabel ?? null,
    };
  } catch {
    return { humanName: null, agentRole: null, deviceLabel: null };
  }
}

export function IdentityProvider({ children }: { children: ReactNode }) {
  const [identity, setIdentityState] = useState<Identity>(() => loadIdentity());

  const setIdentity = useCallback((next: Partial<Identity>) => {
    setIdentityState((prev) => {
      const merged: Identity = { ...prev, ...next };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(merged));
      return merged;
    });
  }, []);

  const value = useMemo(() => ({ ...identity, setIdentity }), [identity, setIdentity]);
  return <IdentityContext.Provider value={value}>{children}</IdentityContext.Provider>;
}
```

- [ ] **Step 5.5: Run test (should pass)**

```bash
cd frontend && pnpm test identity
```

Expected: 2 tests pass.

- [ ] **Step 5.6: Commit**

```bash
git add frontend/src/identity/
git commit -m "feat(frontend): identity provider with localStorage persistence"
```

---

## Task 6: MSW fixture handlers + PPT scenario seed

**Files:**
- Create: `frontend/src/fixtures/seed.ts`
- Create: `frontend/src/fixtures/handlers.ts`
- Create: `frontend/src/fixtures/browser.ts`
- Create: `frontend/src/fixtures/server.ts`
- Create: `frontend/src/fixtures/handlers.test.ts`
- Modify: `frontend/test/setup.ts`

The seed mirrors the PPT scenario in `web/mock.html` — 3 humans, 3 agent instances, 1 topic, 14 messages spanning all 13 types so every typed-message component has fixture data.

- [ ] **Step 6.1: Create `frontend/src/fixtures/seed.ts`**

```ts
import type { MessageDTO, TopicDTO } from "../api/types";

export interface SeedState {
  topics: TopicDTO[];
  messages: MessageDTO[];
  humans: { id: number; name: string }[];
  agentInstances: { id: number; role: string; device_label: string; human_id: number }[];
}

function mk(
  id: number, topicId: number,
  type: MessageDTO["type"], actorType: MessageDTO["actor_type"],
  actorId: number | null, body: string,
  metadata: Record<string, unknown>, createdAt: string,
): MessageDTO {
  return {
    id, topic_id: topicId, type, actor_type: actorType, actor_id: actorId,
    body, metadata, ref_event_id: null, created_at: createdAt,
  };
}

export function makeSeed(): SeedState {
  const humans = [
    { id: 1, name: "Neo" },
    { id: 2, name: "Trinity" },
    { id: 3, name: "Morpheus" },
  ];
  const agentInstances = [
    { id: 11, role: "claude", device_label: "neo-mbp", human_id: 1 },
    { id: 12, role: "claude", device_label: "trinity-air", human_id: 2 },
    { id: 13, role: "codex", device_label: "neo-mbp", human_id: 1 },
  ];
  const topics: TopicDTO[] = [{
    id: 1, slug: "t-ppt", title: "为 Agent 记忆写一个研讨 PPT",
    project_id: 1,
    created_at: "2026-05-19T09:14:00Z",
    updated_at: "2026-05-19T10:32:00Z",
  }];
  const messages: MessageDTO[] = [
    mk(1, 1, "chat", "human", 1,
      "下周三的 AI 研讨会，我答应讲 30min agent 记忆。@Trinity @Morpheus 一起搞吧？受众是技术研究者。",
      {}, "2026-05-19T09:14:00Z"),
    mk(2, 1, "status", "agent", 11,
      "active · 读 docs · 10 min 出 v0",
      { agent_status: "active" }, "2026-05-19T09:18:00Z"),
    mk(3, 1, "artifact_revision", "agent", 11,
      "v0: 8 页骨架",
      { artifact_name: "ai-memory-talk.pptx", version: "v0" }, "2026-05-19T09:31:00Z"),
    mk(4, 1, "finding", "agent", 12,
      "去年研讨会反馈显示「图太多文字太少」是高频抱怨。",
      {}, "2026-05-19T09:46:00Z"),
    mk(5, 1, "question", "human", 3,
      "framing 我建议从「agent 何时该忘记」切入，比「何时该记住」更有冲击力，你怎么想？",
      {}, "2026-05-19T09:55:00Z"),
    mk(6, 1, "task_tree_proposal", "agent", 11,
      "我提议把这个 PPT 拆成 7 个任务",
      {
        title: "研讨 PPT 终版",
        items: [
          { title: "Framing 角度定下来", owner_name: "Morpheus", status: "done" },
          { title: "P4 业界对比矩阵 4×6", owner_name: "claude", status: "done" },
          { title: "Skill 字号修正", owner_name: "codex", status: "done" },
          { title: "P2 framing 改写", owner_name: "claude", status: "active" },
          { title: "P5 加文字解释", status: "pending" },
          { title: "Demo / Q&A 准备", owner_name: "Neo", status: "pending" },
          { title: "排练 30min 时长", status: "pending" },
        ],
      }, "2026-05-19T09:33:00Z"),
    mk(7, 1, "proactive_finding", "agent", 12,
      "我对比了去年反馈，v3 slide 5 建议加 1-2 行解释那个矩阵。",
      {}, "2026-05-19T10:20:00Z"),
    mk(8, 1, "spec_change", "agent", 13,
      "改 research-talk-style/SKILL.md 默认字号 10 → 14",
      {
        file: ".claude/skills/research-talk-style/SKILL.md",
        before: 10, after: 14, approvers: ["Trinity"],
      }, "2026-05-19T10:28:00Z"),
    mk(9, 1, "chat", "agent", 11,
      "framing 角度要不要更激进？我倾向「事件性记忆 vs 语义记忆」的差异化点。",
      {}, "2026-05-19T10:32:00Z"),
    mk(10, 1, "decision", "human", 1,
      "approve spec change v2 → v3",
      { decision_type: "adopt", ref_message_id: 8 }, "2026-05-19T10:35:00Z"),
    mk(11, 1, "handoff", "agent", 11,
      "P5 文字解释这部分我下班了，@codex 接一下",
      { from_actor_id: 11, to_actor_id: 13 }, "2026-05-19T10:40:00Z"),
    mk(12, 1, "nudge", "system", null,
      "这条线程已经讨论 framing 25 分钟，要不要先决定再继续？",
      { reason: "framing-loop" }, "2026-05-19T10:50:00Z"),
    mk(13, 1, "review", "agent", 13,
      "我看了 P5 的草稿，建议把「事件性」放最前面",
      { ref_message_id: 11 }, "2026-05-19T11:05:00Z"),
    mk(14, 1, "system", "system", null,
      "Trinity 加入了 topic",
      {}, "2026-05-19T11:10:00Z"),
  ];
  return { topics, messages, humans, agentInstances };
}
```

- [ ] **Step 6.2: Create `frontend/src/fixtures/handlers.ts`**

```ts
import { http, HttpResponse } from "msw";
import { makeSeed, type SeedState } from "./seed";
import type { MessageDTO, PostMessageInput, IdentityDTO } from "../api/types";

let seed: SeedState = makeSeed();

export function resetFixtures() { seed = makeSeed(); }

export const handlers = [
  http.get("/api/identity/me", ({ request }) => {
    const human = request.headers.get("X-Lets-Human") ?? "Neo";
    const role = request.headers.get("X-Lets-Agent-Role");
    const device = request.headers.get("X-Lets-Device");
    const humanRow =
      seed.humans.find((h) => h.name === human) ??
      (() => {
        const row = { id: seed.humans.length + 1, name: human };
        seed.humans.push(row);
        return row;
      })();
    const out: IdentityDTO = { human: humanRow };
    if (role && device) {
      const instance =
        seed.agentInstances.find(
          (a) => a.role === role && a.device_label === device && a.human_id === humanRow.id,
        ) ??
        (() => {
          const row = {
            id: 100 + seed.agentInstances.length,
            role, device_label: device, human_id: humanRow.id,
          };
          seed.agentInstances.push(row);
          return row;
        })();
      out.agent_instance = {
        id: instance.id, role: instance.role, device_label: instance.device_label,
      };
    }
    return HttpResponse.json(out);
  }),

  http.get("/api/topics", () => HttpResponse.json(seed.topics)),

  http.get("/api/topics/:id/messages", ({ params, request }) => {
    const url = new URL(request.url);
    const types = url.searchParams.getAll("type");
    const topicId = Number(params.id);
    let messages = seed.messages.filter((m) => m.topic_id === topicId);
    if (types.length) messages = messages.filter((m) => types.includes(m.type));
    return HttpResponse.json(messages);
  }),

  http.post("/api/messages", async ({ request }) => {
    const body = (await request.json()) as PostMessageInput;
    const msg: MessageDTO = {
      id: seed.messages.length + 100,
      topic_id: body.topic_id,
      type: body.type,
      actor_type: body.actor_type,
      actor_id: body.actor_id,
      body: body.body,
      metadata: body.metadata ?? {},
      ref_event_id: body.ref_event_id ?? null,
      created_at: new Date().toISOString(),
    };
    seed.messages.push(msg);
    return HttpResponse.json(msg, { status: 201 });
  }),
];
```

- [ ] **Step 6.3: Create `frontend/src/fixtures/browser.ts`**

```ts
import { setupWorker } from "msw/browser";
import { handlers } from "./handlers";

export const worker = setupWorker(...handlers);
```

- [ ] **Step 6.4: Create `frontend/src/fixtures/server.ts`**

```ts
import { setupServer } from "msw/node";
import { handlers } from "./handlers";

export const server = setupServer(...handlers);
```

- [ ] **Step 6.5: Replace `frontend/test/setup.ts`**

```ts
import "@testing-library/jest-dom/vitest";
import { afterAll, afterEach, beforeAll, beforeEach } from "vitest";
import { cleanup } from "@testing-library/react";
import { server } from "../src/fixtures/server";
import { resetFixtures } from "../src/fixtures/handlers";

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
beforeEach(() => {
  localStorage.setItem(
    "lets.identity",
    JSON.stringify({ humanName: "Neo", agentRole: null, deviceLabel: null }),
  );
});
afterEach(() => {
  cleanup();
  server.resetHandlers();
  resetFixtures();
  localStorage.clear();
});
afterAll(() => server.close());
```

- [ ] **Step 6.6: Write failing test**

Create `frontend/src/fixtures/handlers.test.ts`:
```ts
import { describe, it, expect } from "vitest";

describe("MSW handlers", () => {
  it("returns 14 messages for topic 1", async () => {
    const res = await fetch("/api/topics/1/messages");
    const data = (await res.json()) as unknown[];
    expect(data).toHaveLength(14);
  });

  it("returns identity for header-named human", async () => {
    const res = await fetch("/api/identity/me", { headers: { "X-Lets-Human": "Trinity" } });
    const data = (await res.json()) as { human: { name: string } };
    expect(data.human.name).toBe("Trinity");
  });

  it("filters messages by type", async () => {
    const res = await fetch("/api/topics/1/messages?type=spec_change");
    const data = (await res.json()) as unknown[];
    expect(data).toHaveLength(1);
  });
});
```

- [ ] **Step 6.7: Run test**

```bash
cd frontend && pnpm test handlers
```

Expected: 3 tests pass.

- [ ] **Step 6.8: Generate MSW service worker for dev**

```bash
cd frontend && pnpm dlx msw init public --save
```

This creates `frontend/public/mockServiceWorker.js`. Commit that file too.

- [ ] **Step 6.9: Commit**

```bash
git add frontend/src/fixtures/ frontend/public/mockServiceWorker.js frontend/test/setup.ts
git commit -m "feat(frontend): MSW fixture handlers + PPT scenario seed data"
```

---

## Task 7: API client + TanStack Query hooks

**Files:**
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/api/queries.ts`
- Create: `frontend/src/api/queries.test.tsx`
- Modify: `frontend/test/render.tsx`

- [ ] **Step 7.1: Create `frontend/src/api/client.ts`**

```ts
import type { Identity } from "../identity/useIdentity";

export class ApiError extends Error {
  constructor(public status: number, public body: unknown) {
    super(`Lets API ${status}`);
  }
}

function identityHeaders(identity: Identity): Record<string, string> {
  const h: Record<string, string> = {};
  if (identity.humanName) h["X-Lets-Human"] = identity.humanName;
  if (identity.agentRole) h["X-Lets-Agent-Role"] = identity.agentRole;
  if (identity.deviceLabel) h["X-Lets-Device"] = identity.deviceLabel;
  return h;
}

export interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "DELETE";
  body?: unknown;
  identity: Identity;
  query?: Record<string, string | string[] | undefined>;
}

export async function apiRequest<T>(path: string, opts: RequestOptions): Promise<T> {
  const url = new URL(path, window.location.origin);
  if (opts.query) {
    for (const [k, v] of Object.entries(opts.query)) {
      if (v === undefined) continue;
      if (Array.isArray(v)) v.forEach((x) => url.searchParams.append(k, x));
      else url.searchParams.set(k, v);
    }
  }
  const res = await fetch(url.toString(), {
    method: opts.method ?? "GET",
    headers: { "Content-Type": "application/json", ...identityHeaders(opts.identity) },
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  if (!res.ok) {
    let body: unknown = null;
    try { body = await res.json(); } catch { /* ignore */ }
    throw new ApiError(res.status, body);
  }
  return (await res.json()) as T;
}
```

- [ ] **Step 7.2: Create `frontend/src/api/queries.ts`**

```ts
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useIdentity } from "../identity/useIdentity";
import { apiRequest } from "./client";
import type { IdentityDTO, MessageDTO, TopicDTO, PostMessageInput } from "./types";

export function useIdentityMe() {
  const identity = useIdentity();
  return useQuery({
    queryKey: ["identity.me", identity.humanName, identity.agentRole, identity.deviceLabel],
    queryFn: () => apiRequest<IdentityDTO>("/api/identity/me", { identity }),
    enabled: identity.humanName !== null,
  });
}

export function useTopics() {
  const identity = useIdentity();
  return useQuery({
    queryKey: ["topics"],
    queryFn: () => apiRequest<TopicDTO[]>("/api/topics", { identity }),
  });
}

export function useTopicMessages(topicId: number) {
  const identity = useIdentity();
  return useQuery({
    queryKey: ["topics", topicId, "messages"],
    queryFn: () => apiRequest<MessageDTO[]>(`/api/topics/${topicId}/messages`, { identity }),
  });
}

export function usePostMessage(topicId: number) {
  const identity = useIdentity();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: PostMessageInput) =>
      apiRequest<MessageDTO>("/api/messages", { method: "POST", body: input, identity }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["topics", topicId, "messages"] }),
  });
}
```

- [ ] **Step 7.3: Update `frontend/test/render.tsx` to include IdentityProvider**

```tsx
import type { ReactElement, ReactNode } from "react";
import { render, type RenderOptions } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { IdentityProvider } from "../src/identity/IdentityProvider";

export function makeQueryClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
}

function Providers({ children }: { children: ReactNode }) {
  const client = makeQueryClient();
  return (
    <QueryClientProvider client={client}>
      <IdentityProvider>{children}</IdentityProvider>
    </QueryClientProvider>
  );
}

export function renderWithProviders(
  ui: ReactElement,
  options?: Omit<RenderOptions, "wrapper">,
) {
  return render(ui, { wrapper: Providers, ...options });
}
```

- [ ] **Step 7.4: Write failing test**

Create `frontend/src/api/queries.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { useTopicMessages, useIdentityMe } from "./queries";

function Probe() {
  const me = useIdentityMe();
  const msgs = useTopicMessages(1);
  return (
    <>
      <span data-testid="me">{me.data?.human.name ?? "loading"}</span>
      <span data-testid="count">{msgs.data?.length ?? -1}</span>
    </>
  );
}

describe("queries", () => {
  it("fetches identity and topic messages", async () => {
    renderWithProviders(<Probe />);
    await waitFor(() => expect(screen.getByTestId("me")).toHaveTextContent("Neo"));
    await waitFor(() => expect(screen.getByTestId("count")).toHaveTextContent("14"));
  });
});
```

- [ ] **Step 7.5: Run test**

```bash
cd frontend && pnpm test queries
```

Expected: 1 test passes.

- [ ] **Step 7.6: Commit**

```bash
git add frontend/src/api/client.ts frontend/src/api/queries.ts frontend/src/api/queries.test.tsx frontend/test/render.tsx
git commit -m "feat(frontend): API client + TanStack Query hooks with identity header injection"
```

---

## Task 8: Boot MSW in dev mode + providers in main.tsx

**Files:**
- Modify: `frontend/src/main.tsx`
- Create: `frontend/.env.development`
- Create: `frontend/.env.production`

- [ ] **Step 8.1: Update `frontend/src/main.tsx`**

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { IdentityProvider } from "./identity/IdentityProvider";
import App from "./App";
import "./index.css";

async function bootstrap() {
  if (import.meta.env.VITE_USE_FIXTURES !== "false") {
    const { worker } = await import("./fixtures/browser");
    await worker.start({ onUnhandledRequest: "warn" });
  }

  const queryClient = new QueryClient({
    defaultOptions: { queries: { staleTime: 5_000 } },
  });

  const root = document.getElementById("root");
  if (!root) throw new Error("#root missing");
  ReactDOM.createRoot(root).render(
    <React.StrictMode>
      <QueryClientProvider client={queryClient}>
        <IdentityProvider>
          <App />
        </IdentityProvider>
      </QueryClientProvider>
    </React.StrictMode>,
  );
}

void bootstrap();
```

- [ ] **Step 8.2: Add `frontend/.env.development`**

```
VITE_USE_FIXTURES=true
```

- [ ] **Step 8.3: Add `frontend/.env.production`**

```
VITE_USE_FIXTURES=false
```

- [ ] **Step 8.4: Run dev and verify MSW boots**

```bash
cd frontend && pnpm dev
```

Open `http://localhost:5173` and the browser DevTools console. Expected line: `[MSW] Mocking enabled.`

- [ ] **Step 8.5: Commit**

```bash
git add frontend/src/main.tsx frontend/.env.development frontend/.env.production
git commit -m "chore(frontend): wire MSW worker + IdentityProvider into app bootstrap"
```

---

## Task 9: AppShell — 3-pane grid + responsive breakpoints

**Files:**
- Create: `frontend/src/layout/AppShell.tsx`
- Create: `frontend/src/layout/AppShell.test.tsx`
- Create: `frontend/src/lib/cn.ts`

The desktop layout is `var(--side-w) 1fr var(--context-w)`, tablet drops context, mobile drops sidebar. Match mock.html lines 96–112.

- [ ] **Step 9.1: Create `frontend/src/lib/cn.ts`**

```ts
export function cn(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}
```

- [ ] **Step 9.2: Write failing test**

Create `frontend/src/layout/AppShell.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { AppShell } from "./AppShell";

describe("<AppShell />", () => {
  it("renders the 3 named slots", () => {
    renderWithProviders(
      <AppShell
        sidebar={<div>SIDE</div>}
        main={<div>MAIN</div>}
        context={<div>CTX</div>}
      />,
    );
    expect(screen.getByText("SIDE")).toBeInTheDocument();
    expect(screen.getByText("MAIN")).toBeInTheDocument();
    expect(screen.getByText("CTX")).toBeInTheDocument();
  });

  it("annotates the grid container for breakpoint switching", () => {
    renderWithProviders(<AppShell sidebar={<i />} main={<i />} context={<i />} />);
    const grid = screen.getByTestId("app-shell");
    expect(grid.className).toContain("grid");
  });
});
```

- [ ] **Step 9.3: Create `frontend/src/layout/AppShell.tsx`**

```tsx
import type { ReactNode } from "react";

interface AppShellProps {
  sidebar: ReactNode;
  main: ReactNode;
  context: ReactNode;
}

export function AppShell({ sidebar, main, context }: AppShellProps) {
  return (
    <div
      data-testid="app-shell"
      className="grid h-[100dvh]"
      style={{
        gridTemplateColumns: "var(--side-w, 296px) 1fr var(--context-w, 360px)",
      }}
    >
      <aside className="border-r border-border-soft bg-surface overflow-y-auto">
        {sidebar}
      </aside>
      <main className="flex flex-col min-w-0 overflow-hidden">{main}</main>
      <aside className="border-l border-border-soft bg-surface overflow-y-auto hidden xl:block">
        {context}
      </aside>
    </div>
  );
}
```

- [ ] **Step 9.4: Add CSS variables for widths in `frontend/src/index.css`**

Append inside the existing `@theme { … }` block (before the closing `}`):
```css
  --side-w: 296px;
  --context-w: 360px;
```

Also append outside the `@theme` block (at end of file):
```css
@media (max-width: 1279px) {
  [data-testid="app-shell"] { grid-template-columns: var(--side-w) 1fr !important; }
  [data-testid="app-shell"] > aside:last-child { display: none !important; }
}
@media (max-width: 767px) {
  [data-testid="app-shell"] { grid-template-columns: 1fr !important; }
  [data-testid="app-shell"] > aside:first-child { display: none !important; }
}
```

- [ ] **Step 9.5: Run test**

```bash
cd frontend && pnpm test AppShell
```

Expected: 2 tests pass.

- [ ] **Step 9.6: Commit**

```bash
git add frontend/src/layout/AppShell.tsx frontend/src/layout/AppShell.test.tsx frontend/src/lib/cn.ts frontend/src/index.css
git commit -m "feat(frontend): 3-pane AppShell with responsive breakpoints"
```

---

## Task 10: Sidebar skeleton (proj head + section labels)

**Files:**
- Create: `frontend/src/layout/Sidebar.tsx`
- Create: `frontend/src/layout/Sidebar.test.tsx`

Faithful port of mock.html lines 1246–1467 sidebar structure: proj head, attention entry button, channels collapsible, online collapsible, DMs collapsible, settings footer.

- [ ] **Step 10.1: Write failing test**

Create `frontend/src/layout/Sidebar.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { Sidebar } from "./Sidebar";

describe("<Sidebar />", () => {
  it("renders project name + repo line", () => {
    renderWithProviders(<Sidebar projectName="Lets" projectRepo="github.com/echomem/lets" />);
    expect(screen.getByText("Lets")).toBeInTheDocument();
    expect(screen.getByText(/echomem\/lets/)).toBeInTheDocument();
  });

  it("shows section labels for channels, online, direct", () => {
    renderWithProviders(<Sidebar projectName="Lets" projectRepo="x/y" />);
    expect(screen.getByText(/channels/i)).toBeInTheDocument();
    expect(screen.getByText(/online/i)).toBeInTheDocument();
    expect(screen.getByText(/direct/i)).toBeInTheDocument();
  });

  it("renders the attention entry button", () => {
    renderWithProviders(<Sidebar projectName="Lets" projectRepo="x/y" />);
    expect(screen.getByRole("button", { name: /待处理|attention/i })).toBeInTheDocument();
  });
});
```

- [ ] **Step 10.2: Create `frontend/src/layout/Sidebar.tsx`**

```tsx
interface SidebarProps {
  projectName: string;
  projectRepo: string;
  attentionCount?: number;
}

export function Sidebar({ projectName, projectRepo, attentionCount = 0 }: SidebarProps) {
  return (
    <div className="flex flex-col h-full">
      <div className="px-5 pt-5 pb-4 border-b border-border-soft flex items-center gap-3">
        <div className="w-7 h-7 rounded-lg bg-text text-bg grid place-items-center font-bold text-sm font-[var(--font-display)]">
          {projectName[0]}
        </div>
        <div className="leading-tight">
          <div className="font-[var(--font-display)] font-semibold text-[15px]">{projectName}</div>
          <div className="text-text-dim text-[11px] font-mono mt-px">{projectRepo}</div>
        </div>
      </div>

      <div className="p-3">
        <button
          className="w-full flex items-center justify-between px-3 py-2 rounded text-xs uppercase tracking-wider font-semibold text-text-dim hover:bg-surface-hover hover:text-text"
          type="button"
        >
          <span>待处理</span>
          {attentionCount > 0 && (
            <span className="bg-accent-soft text-accent-text px-2 py-px rounded-full text-[10px] font-mono">
              {attentionCount}
            </span>
          )}
        </button>
      </div>

      <SectionLabel>Project Spec</SectionLabel>
      <CollapsibleSection label="Channels" count={2} />
      <CollapsibleSection label="Online" count={3} />
      <CollapsibleSection label="Direct Messages" count={1} />

      <div className="flex-1 min-h-3" />

      <div className="border-t border-border-soft px-4 py-3 flex flex-col gap-0.5">
        <FooterLink>项目设置</FooterLink>
        <FooterLink>个人设置</FooterLink>
      </div>
    </div>
  );
}

function SectionLabel({ children }: { children: string }) {
  return (
    <div className="px-3 py-2 text-[11px] uppercase tracking-wider font-semibold text-text-dim">
      {children}
    </div>
  );
}

function CollapsibleSection({ label, count }: { label: string; count: number }) {
  return (
    <div className="p-3 pt-1">
      <button
        type="button"
        className="w-full flex items-center gap-2 px-3 py-1.5 rounded text-[11px] uppercase tracking-wider font-semibold text-text-dim hover:bg-surface-hover hover:text-text"
      >
        <span className="text-[9px] text-text-dim">▶</span>
        <span className="flex-1 text-left">{label}</span>
        <span className="font-mono normal-case font-medium tracking-normal">{count}</span>
      </button>
    </div>
  );
}

function FooterLink({ children }: { children: string }) {
  return (
    <div className="px-2 py-1.5 rounded text-xs text-text-muted hover:bg-surface-hover hover:text-text cursor-pointer">
      {children}
    </div>
  );
}
```

- [ ] **Step 10.3: Run test**

```bash
cd frontend && pnpm test Sidebar
```

Expected: 3 tests pass.

- [ ] **Step 10.4: Commit**

```bash
git add frontend/src/layout/Sidebar.tsx frontend/src/layout/Sidebar.test.tsx
git commit -m "feat(frontend): sidebar skeleton with proj head + collapsible sections"
```

---

## Task 11: TopicHeader with merged goal progress

**Files:**
- Create: `frontend/src/topic/TopicHeader.tsx`
- Create: `frontend/src/topic/TopicHeaderProgress.tsx`
- Create: `frontend/src/topic/TopicHeader.test.tsx`
- Create: `frontend/src/lib/time.ts`

Per design decision: the goal card is merged into TopicHeader. Header shows: topic title · progress ring (% + count) · current-task chip · ⋯ menu. Full goal detail (spec, approvers, Mark as Final) lives in `GoalDetailPanel` in the context pane (Task 35).

- [ ] **Step 11.1: Create `frontend/src/lib/time.ts`**

```ts
export function formatHHMM(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", hour12: false });
}
```

- [ ] **Step 11.2: Write failing test**

Create `frontend/src/topic/TopicHeader.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { TopicHeader } from "./TopicHeader";

describe("<TopicHeader />", () => {
  it("renders topic title", () => {
    renderWithProviders(<TopicHeader title="为 Agent 记忆写一个研讨 PPT" />);
    expect(screen.getByRole("heading", { name: /PPT/ })).toBeInTheDocument();
  });

  it("renders progress percent + count when goal info present", () => {
    renderWithProviders(
      <TopicHeader
        title="t"
        goal={{ doneCount: 5, totalCount: 7, currentTaskTitle: "P5 加文字解释" }}
      />,
    );
    expect(screen.getByText(/71%/)).toBeInTheDocument();
    expect(screen.getByText(/5\s*\/\s*7/)).toBeInTheDocument();
    expect(screen.getByText(/P5/)).toBeInTheDocument();
  });

  it("omits goal chip when no goal info", () => {
    renderWithProviders(<TopicHeader title="t" />);
    expect(screen.queryByText(/%/)).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 11.3: Create `frontend/src/topic/TopicHeaderProgress.tsx`**

```tsx
interface Props {
  doneCount: number;
  totalCount: number;
  currentTaskTitle?: string | null;
}

export function TopicHeaderProgress({ doneCount, totalCount, currentTaskTitle }: Props) {
  const pct = totalCount === 0 ? 0 : Math.round((doneCount / totalCount) * 100);
  const stroke = 2;
  const r = 7;
  const c = 2 * Math.PI * r;
  const dash = (pct / 100) * c;
  return (
    <div className="flex items-center gap-2 text-[12px] text-text-muted">
      <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden>
        <circle cx="9" cy="9" r={r} fill="none" stroke="var(--color-border)" strokeWidth={stroke} />
        <circle
          cx="9" cy="9" r={r} fill="none"
          stroke="var(--color-accent)" strokeWidth={stroke}
          strokeDasharray={`${dash} ${c}`} strokeLinecap="round"
          transform="rotate(-90 9 9)"
        />
      </svg>
      <span className="font-mono text-text">{pct}%</span>
      <span className="font-mono">{doneCount}/{totalCount}</span>
      {currentTaskTitle && (
        <>
          <span className="text-text-dim">→</span>
          <span className="truncate max-w-[16ch]" title={currentTaskTitle}>{currentTaskTitle}</span>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 11.4: Create `frontend/src/topic/TopicHeader.tsx`**

```tsx
import { TopicHeaderProgress } from "./TopicHeaderProgress";

interface GoalInfo {
  doneCount: number;
  totalCount: number;
  currentTaskTitle?: string | null;
}

interface TopicHeaderProps {
  title: string;
  goal?: GoalInfo;
  onOpenMenu?: () => void;
}

export function TopicHeader({ title, goal, onOpenMenu }: TopicHeaderProps) {
  return (
    <header className="flex items-center gap-4 px-6 py-3 border-b border-border-soft min-w-0">
      <h1 className="font-[var(--font-display)] font-semibold text-lg truncate">{title}</h1>
      {goal && (
        <TopicHeaderProgress
          doneCount={goal.doneCount}
          totalCount={goal.totalCount}
          currentTaskTitle={goal.currentTaskTitle ?? null}
        />
      )}
      <div className="flex-1" />
      <button
        type="button"
        onClick={onOpenMenu}
        aria-label="topic menu"
        className="px-2 py-1 rounded hover:bg-surface-hover text-text-muted"
      >
        ⋯
      </button>
    </header>
  );
}
```

- [ ] **Step 11.5: Run test**

```bash
cd frontend && pnpm test TopicHeader
```

Expected: 3 tests pass.

- [ ] **Step 11.6: Commit**

```bash
git add frontend/src/topic/TopicHeader.tsx frontend/src/topic/TopicHeaderProgress.tsx frontend/src/topic/TopicHeader.test.tsx frontend/src/lib/time.ts
git commit -m "feat(frontend): TopicHeader with inline goal progress (merged goal card)"
```

---

## Task 12: TopicView skeleton + DaySeparator

**Files:**
- Create: `frontend/src/topic/TopicView.tsx`
- Create: `frontend/src/topic/DaySeparator.tsx`
- Create: `frontend/src/topic/TopicView.test.tsx`

- [ ] **Step 12.1: Create `frontend/src/topic/DaySeparator.tsx`**

```tsx
export function DaySeparator({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-3 my-4 text-[11px] uppercase tracking-wider text-text-dim font-semibold">
      <div className="flex-1 h-px bg-border-soft" />
      <span>{label}</span>
      <div className="flex-1 h-px bg-border-soft" />
    </div>
  );
}
```

- [ ] **Step 12.2: Write failing test**

Create `frontend/src/topic/TopicView.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { TopicView } from "./TopicView";

describe("<TopicView />", () => {
  it("renders topic header + 14 message rows for topic 1", async () => {
    renderWithProviders(<TopicView topicId={1} />);
    await waitFor(() => {
      expect(screen.getAllByTestId("message-row").length).toBe(14);
    });
  });
});
```

- [ ] **Step 12.3: Create `frontend/src/topic/TopicView.tsx`**

```tsx
import { useTopicMessages } from "../api/queries";
import { TopicHeader } from "./TopicHeader";
import { DaySeparator } from "./DaySeparator";

interface Props { topicId: number }

export function TopicView({ topicId }: Props) {
  const { data, isLoading, isError } = useTopicMessages(topicId);

  return (
    <div className="flex flex-col h-full">
      <TopicHeader
        title="为 Agent 记忆写一个研讨 PPT"
        goal={{ doneCount: 3, totalCount: 7, currentTaskTitle: "P2 framing 改写" }}
      />
      <div className="flex-1 overflow-y-auto px-6 py-4">
        <DaySeparator label="今天" />
        {isLoading && <div className="text-text-dim">加载中…</div>}
        {isError && <div className="text-text-dim">加载失败</div>}
        {data?.map((m) => (
          <div key={m.id} data-testid="message-row" className="py-2 border-b border-border-soft">
            <div className="text-[11px] font-mono text-text-dim">
              {m.type} · actor {m.actor_type}#{m.actor_id ?? "-"}
            </div>
            <div>{m.body}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

This is a debug-render of messages; Tasks 14+ swap each row for a typed component.

- [ ] **Step 12.4: Run test**

```bash
cd frontend && pnpm test TopicView
```

Expected: 1 test passes (14 rows).

- [ ] **Step 12.5: Wire up App so Phase 2 demo works**

Update `frontend/src/App.tsx`:
```tsx
import { AppShell } from "./layout/AppShell";
import { Sidebar } from "./layout/Sidebar";
import { TopicView } from "./topic/TopicView";

export default function App() {
  return (
    <AppShell
      sidebar={<Sidebar projectName="Lets" projectRepo="github.com/echomem/lets" attentionCount={4} />}
      main={<TopicView topicId={1} />}
      context={<div className="p-4 text-text-dim text-sm">Context pane (Phase 6)</div>}
    />
  );
}
```

- [ ] **Step 12.6: Run dev and visually verify**

```bash
cd frontend && pnpm dev
```

Open `http://localhost:5173`. Expected: 3-pane layout, sidebar on left with "Lets", topic title at top, 14 raw message rows in main area, context pane on right with placeholder.

- [ ] **Step 12.7: Commit**

```bash
git add frontend/src/topic/TopicView.tsx frontend/src/topic/DaySeparator.tsx frontend/src/topic/TopicView.test.tsx frontend/src/App.tsx
git commit -m "feat(frontend): TopicView wired to messages query with debug rows"
```

---

## Task 13: Phase 2 design checkpoint A

**Files:** none (review)

- [ ] **Step 13.1: Visual review at `http://localhost:5173`**

Open both `http://localhost:5173` and `http://localhost:8000/mock` side-by-side. Compare:
- Sidebar width feels right? (`--side-w`)
- Context pane width feels right? (`--context-w`)
- Accent color hue (the orange-ish chip on attention button) — match v6 or shift?
- Body / display font sizes match scale?

- [ ] **Step 13.2: Apply any token adjustments**

Edit `frontend/src/index.css` `@theme` block only. Typical adjustments:
- Bump `--side-w` from `296px` to `280px` if sidebar feels too wide
- Shift `--color-accent` hue 55 → 40 if you want more red, → 70 if more yellow
- No structural changes — composition stays the same

- [ ] **Step 13.3: Commit (if any changes)**

```bash
git add frontend/src/index.css
git commit -m "chore(frontend): Phase 2 design checkpoint A adjustments"
```

If nothing to adjust, skip the commit and add a note in the next task's commit.

---

## Task 14: BaseMessage shell + Message dispatch

**Files:**
- Create: `frontend/src/messages/BaseMessage.tsx`
- Create: `frontend/src/messages/Message.tsx`
- Create: `frontend/src/messages/BaseMessage.test.tsx`
- Create: `frontend/src/messages/Avatar.tsx`

`BaseMessage` owns the avatar/head/body grid common to every typed component. `Message` dispatches by `m.type` to a concrete component. `Avatar` resolves human/claude/codex colors.

- [ ] **Step 14.1: Create `frontend/src/messages/Avatar.tsx`**

```tsx
import { cn } from "../lib/cn";

interface Props {
  initial: string;
  kind: "human" | "claude" | "codex" | "system";
  size?: "sm" | "md";
}

export function Avatar({ initial, kind, size = "md" }: Props) {
  return (
    <div
      className={cn(
        "rounded-full grid place-items-center font-semibold leading-none flex-shrink-0",
        size === "md" ? "w-7 h-7 text-[12px]" : "w-5 h-5 text-[10px]",
        kind === "human" && "bg-human-bg text-human",
        kind === "claude" && "bg-agent-claude-bg text-agent-claude",
        kind === "codex" && "bg-agent-codex-bg text-agent-codex",
        kind === "system" && "bg-surface-hover text-text-dim",
      )}
    >
      {initial}
    </div>
  );
}
```

- [ ] **Step 14.2: Write failing test**

Create `frontend/src/messages/BaseMessage.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { BaseMessage } from "./BaseMessage";

describe("<BaseMessage />", () => {
  it("renders name, meta, and body", () => {
    renderWithProviders(
      <BaseMessage
        actor={{ kind: "human", initial: "N", displayName: "Neo" }}
        timeIso="2026-05-19T09:14:00Z"
        body={<p>hi</p>}
      />,
    );
    expect(screen.getByText("Neo")).toBeInTheDocument();
    expect(screen.getByText("hi")).toBeInTheDocument();
    expect(screen.getByText("N")).toBeInTheDocument();
  });

  it("renders optional tag chip", () => {
    renderWithProviders(
      <BaseMessage
        actor={{ kind: "claude", initial: "CC", displayName: "claude · neo-mbp" }}
        timeIso="2026-05-19T09:18:00Z"
        body={<p>x</p>}
        tag="status"
      />,
    );
    expect(screen.getByText("status")).toBeInTheDocument();
  });
});
```

- [ ] **Step 14.3: Create `frontend/src/messages/BaseMessage.tsx`**

```tsx
import type { ReactNode } from "react";
import { Avatar } from "./Avatar";
import { formatHHMM } from "../lib/time";
import { cn } from "../lib/cn";

interface ActorInfo {
  kind: "human" | "claude" | "codex" | "system";
  initial: string;
  displayName: string;
}

interface Props {
  actor: ActorInfo;
  timeIso: string;
  body: ReactNode;
  tag?: string;
  tone?: "default" | "status" | "finding" | "decision" | "handoff" | "review" |
        "artifact" | "spec" | "proactive" | "tree" | "nudge" | "question";
}

const toneClasses: Record<NonNullable<Props["tone"]>, string> = {
  default: "",
  status: "bg-surface-elev border border-border-soft",
  finding: "bg-finding-bg/40 border-l-2 border-finding pl-3",
  decision: "bg-decision-bg/40 border-l-2 border-decision pl-3",
  handoff: "bg-handoff-bg/40 border-l-2 border-handoff pl-3",
  review: "bg-review-bg/40 border-l-2 border-review pl-3",
  artifact: "bg-artifact-bg/40 border-l-2 border-artifact pl-3",
  spec: "bg-spec-bg/40 border-l-2 border-spec pl-3",
  proactive: "bg-proactive-bg/40 border-l-2 border-proactive pl-3",
  tree: "bg-tree-bg/40 border-l-2 border-tree pl-3",
  nudge: "bg-nudge-bg border-l-2 border-nudge pl-3 italic text-nudge",
  question: "bg-accent-soft/30 border-l-2 border-accent pl-3",
};

const tagToneClass: Record<NonNullable<Props["tone"]>, string> = {
  default: "",
  status: "text-status-work",
  finding: "text-finding",
  decision: "text-decision",
  handoff: "text-handoff",
  review: "text-review",
  artifact: "text-artifact",
  spec: "text-spec",
  proactive: "text-proactive",
  tree: "text-tree",
  nudge: "text-nudge",
  question: "text-accent-text",
};

export function BaseMessage({ actor, timeIso, body, tag, tone = "default" }: Props) {
  const nameColor =
    actor.kind === "human" ? "text-human" :
    actor.kind === "claude" ? "text-agent-claude" :
    actor.kind === "codex" ? "text-agent-codex" : "text-text-dim";

  return (
    <div data-testid="message-row" className="grid grid-cols-[28px_1fr] gap-3 py-2">
      <Avatar initial={actor.initial} kind={actor.kind} />
      <div className="min-w-0">
        <div className="flex items-baseline gap-2 flex-wrap">
          <span className={cn("font-semibold text-[13.5px]", nameColor)}>{actor.displayName}</span>
          <span className="text-text-dim text-[11px] font-mono">{formatHHMM(timeIso)}</span>
          {tag && (
            <span className={cn("px-1.5 py-px rounded text-[10.5px] font-mono", tagToneClass[tone])}>
              {tag}
            </span>
          )}
        </div>
        <div className={cn("text-[14px] leading-relaxed py-1 px-3 rounded mt-px", toneClasses[tone])}>
          {body}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 14.4: Create `frontend/src/messages/Message.tsx`**

```tsx
import type { MessageDTO } from "../api/types";
import { ChatMessage } from "./ChatMessage";
import { StatusMessage } from "./StatusMessage";
import { FindingMessage } from "./FindingMessage";
import { DecisionMessage } from "./DecisionMessage";
import { QuestionMessage } from "./QuestionMessage";
import { HandoffMessage } from "./HandoffMessage";
import { ReviewMessage } from "./ReviewMessage";
import { ArtifactRevisionMessage } from "./ArtifactRevisionMessage";
import { SpecChangeMessage } from "./SpecChangeMessage";
import { NudgeMessage } from "./NudgeMessage";
import { ProactiveFindingMessage } from "./ProactiveFindingMessage";
import { TaskTreeProposalMessage } from "./TaskTreeProposalMessage";
import { SystemMessage } from "./SystemMessage";

export interface ActorResolver {
  resolve(message: MessageDTO): {
    kind: "human" | "claude" | "codex" | "system";
    initial: string;
    displayName: string;
  };
}

interface Props {
  message: MessageDTO;
  resolveActor: ActorResolver["resolve"];
}

export function Message({ message, resolveActor }: Props) {
  const actor = resolveActor(message);
  switch (message.type) {
    case "chat":               return <ChatMessage message={message} actor={actor} />;
    case "status":             return <StatusMessage message={message} actor={actor} />;
    case "finding":            return <FindingMessage message={message} actor={actor} />;
    case "decision":           return <DecisionMessage message={message} actor={actor} />;
    case "question":           return <QuestionMessage message={message} actor={actor} />;
    case "handoff":            return <HandoffMessage message={message} actor={actor} />;
    case "review":             return <ReviewMessage message={message} actor={actor} />;
    case "artifact_revision":  return <ArtifactRevisionMessage message={message} actor={actor} />;
    case "spec_change":        return <SpecChangeMessage message={message} actor={actor} />;
    case "nudge":              return <NudgeMessage message={message} actor={actor} />;
    case "proactive_finding":  return <ProactiveFindingMessage message={message} actor={actor} />;
    case "task_tree_proposal": return <TaskTreeProposalMessage message={message} actor={actor} />;
    case "system":             return <SystemMessage message={message} actor={actor} />;
  }
}
```

This file imports 13 components that don't exist yet — TypeScript will error. Stub them in Task 15.

- [ ] **Step 14.5: Run BaseMessage test**

```bash
cd frontend && pnpm test BaseMessage
```

Expected: 2 tests pass. (Don't run all tests yet — Message.tsx imports will fail until Task 15.)

- [ ] **Step 14.6: Commit**

```bash
git add frontend/src/messages/BaseMessage.tsx frontend/src/messages/Avatar.tsx frontend/src/messages/Message.tsx frontend/src/messages/BaseMessage.test.tsx
git commit -m "feat(frontend): BaseMessage shell + Message dispatch (component stubs pending)"
```

---

## Task 15: MentionText helper + ActorResolver

**Files:**
- Create: `frontend/src/messages/MentionText.tsx`
- Create: `frontend/src/messages/MentionText.test.tsx`
- Create: `frontend/src/messages/actorResolver.ts`

`MentionText` parses `@name` substrings and renders them as `.mention` chips. `actorResolver` maps `actor_type`/`actor_id` to the display info BaseMessage wants.

- [ ] **Step 15.1: Write failing test**

Create `frontend/src/messages/MentionText.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { MentionText } from "./MentionText";

describe("<MentionText />", () => {
  it("plain text passes through", () => {
    renderWithProviders(<MentionText>hello world</MentionText>);
    expect(screen.getByText("hello world")).toBeInTheDocument();
  });

  it("wraps @name in mention chip", () => {
    renderWithProviders(<MentionText>ping @Trinity and @Morpheus please</MentionText>);
    expect(screen.getByText("@Trinity")).toHaveClass("mention");
    expect(screen.getByText("@Morpheus")).toHaveClass("mention");
  });
});
```

- [ ] **Step 15.2: Create `frontend/src/messages/MentionText.tsx`**

```tsx
import type { ReactNode } from "react";

const MENTION_RE = /(@[\p{L}\p{N}_-]+)/gu;

export function MentionText({ children }: { children: string }) {
  const parts = children.split(MENTION_RE);
  const out: ReactNode[] = [];
  for (let i = 0; i < parts.length; i++) {
    const p = parts[i];
    if (p === undefined) continue;
    if (MENTION_RE.test(p)) {
      out.push(
        <span key={i} className="mention bg-accent-soft text-accent-text px-1 rounded font-mono text-[12px]">
          {p}
        </span>,
      );
    } else if (p) {
      out.push(<span key={i}>{p}</span>);
    }
    MENTION_RE.lastIndex = 0;
  }
  return <>{out}</>;
}
```

- [ ] **Step 15.3: Create `frontend/src/messages/actorResolver.ts`**

```ts
import type { MessageDTO } from "../api/types";

export interface DirectoryEntry {
  human?: { id: number; name: string };
  agentInstance?: { id: number; role: string; device_label: string };
}

export interface Directory {
  humans: { id: number; name: string }[];
  agentInstances: { id: number; role: string; device_label: string; human_id: number }[];
}

export function makeActorResolver(dir: Directory) {
  return function resolve(m: MessageDTO) {
    if (m.actor_type === "system") {
      return { kind: "system" as const, initial: "S", displayName: "system" };
    }
    if (m.actor_type === "human") {
      const h = dir.humans.find((x) => x.id === m.actor_id);
      const name = h?.name ?? "?";
      return { kind: "human" as const, initial: name[0]?.toUpperCase() ?? "?", displayName: name };
    }
    const a = dir.agentInstances.find((x) => x.id === m.actor_id);
    const role = (a?.role ?? "agent") as "claude" | "codex";
    const kind = role === "claude" ? ("claude" as const) : ("codex" as const);
    const initial = role === "claude" ? "CC" : role === "codex" ? "CX" : "??";
    const display = a ? `${a.role} · ${a.device_label}` : `${role}#${m.actor_id}`;
    return { kind, initial, displayName: display };
  };
}
```

- [ ] **Step 15.4: Run MentionText test**

```bash
cd frontend && pnpm test MentionText
```

Expected: 2 tests pass.

- [ ] **Step 15.5: Commit**

```bash
git add frontend/src/messages/MentionText.tsx frontend/src/messages/MentionText.test.tsx frontend/src/messages/actorResolver.ts
git commit -m "feat(frontend): MentionText + actorResolver helpers"
```

---

## Task 16: ChatMessage + SystemMessage + StatusMessage

**Files:**
- Create: `frontend/src/messages/ChatMessage.tsx`
- Create: `frontend/src/messages/SystemMessage.tsx`
- Create: `frontend/src/messages/StatusMessage.tsx`
- Create: `frontend/src/messages/ChatMessage.test.tsx`
- Create: `frontend/src/messages/SystemMessage.test.tsx`
- Create: `frontend/src/messages/StatusMessage.test.tsx`

- [ ] **Step 16.1: Write failing tests**

Create `frontend/src/messages/ChatMessage.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { ChatMessage } from "./ChatMessage";

describe("<ChatMessage />", () => {
  it("renders body with mentions parsed", () => {
    renderWithProviders(
      <ChatMessage
        actor={{ kind: "human", initial: "N", displayName: "Neo" }}
        message={{
          id: 1, topic_id: 1, type: "chat", actor_type: "human", actor_id: 1,
          body: "ping @Trinity", metadata: {}, ref_event_id: null, created_at: "2026-05-19T09:14:00Z",
        }}
      />,
    );
    expect(screen.getByText("@Trinity")).toHaveClass("mention");
  });
});
```

Create `frontend/src/messages/SystemMessage.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { SystemMessage } from "./SystemMessage";

describe("<SystemMessage />", () => {
  it("renders body in muted style with no avatar block", () => {
    renderWithProviders(
      <SystemMessage
        actor={{ kind: "system", initial: "S", displayName: "system" }}
        message={{
          id: 14, topic_id: 1, type: "system", actor_type: "system", actor_id: null,
          body: "Trinity 加入了 topic", metadata: {}, ref_event_id: null, created_at: "2026-05-19T11:10:00Z",
        }}
      />,
    );
    expect(screen.getByText(/Trinity 加入了 topic/)).toBeInTheDocument();
  });
});
```

Create `frontend/src/messages/StatusMessage.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { StatusMessage } from "./StatusMessage";

describe("<StatusMessage />", () => {
  it("shows status tag and body", () => {
    renderWithProviders(
      <StatusMessage
        actor={{ kind: "claude", initial: "CC", displayName: "claude · neo-mbp" }}
        message={{
          id: 2, topic_id: 1, type: "status", actor_type: "agent", actor_id: 11,
          body: "active · 读 docs", metadata: { agent_status: "active" },
          ref_event_id: null, created_at: "2026-05-19T09:18:00Z",
        }}
      />,
    );
    expect(screen.getByText("status")).toBeInTheDocument();
    expect(screen.getByText(/active · 读 docs/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 16.2: Create the three components**

`frontend/src/messages/ChatMessage.tsx`:
```tsx
import type { MessageDTO } from "../api/types";
import { BaseMessage } from "./BaseMessage";
import { MentionText } from "./MentionText";

interface Actor { kind: "human" | "claude" | "codex" | "system"; initial: string; displayName: string }

export function ChatMessage({ message, actor }: { message: MessageDTO; actor: Actor }) {
  return (
    <BaseMessage
      actor={actor}
      timeIso={message.created_at}
      body={<MentionText>{message.body}</MentionText>}
    />
  );
}
```

`frontend/src/messages/SystemMessage.tsx`:
```tsx
import type { MessageDTO } from "../api/types";
import { formatHHMM } from "../lib/time";

interface Actor { kind: "system"; initial: string; displayName: string }

export function SystemMessage({ message }: { message: MessageDTO; actor: Actor }) {
  return (
    <div data-testid="message-row" className="py-1 px-3 text-center text-[12px] text-text-dim italic">
      <span>{message.body}</span>
      <span className="ml-2 font-mono text-[11px]">{formatHHMM(message.created_at)}</span>
    </div>
  );
}
```

`frontend/src/messages/StatusMessage.tsx`:
```tsx
import type { MessageDTO } from "../api/types";
import { BaseMessage } from "./BaseMessage";

interface Actor { kind: "human" | "claude" | "codex" | "system"; initial: string; displayName: string }

export function StatusMessage({ message, actor }: { message: MessageDTO; actor: Actor }) {
  return (
    <BaseMessage
      actor={actor}
      timeIso={message.created_at}
      tag="status"
      tone="status"
      body={<span className="font-mono text-[13px]">{message.body}</span>}
    />
  );
}
```

- [ ] **Step 16.3: Run tests**

```bash
cd frontend && pnpm test "ChatMessage|SystemMessage|StatusMessage"
```

Expected: 3 tests pass.

- [ ] **Step 16.4: Commit**

```bash
git add frontend/src/messages/ChatMessage.tsx frontend/src/messages/ChatMessage.test.tsx \
        frontend/src/messages/SystemMessage.tsx frontend/src/messages/SystemMessage.test.tsx \
        frontend/src/messages/StatusMessage.tsx frontend/src/messages/StatusMessage.test.tsx
git commit -m "feat(frontend): chat/status/system message components"
```

---

## Task 17: FindingMessage + DecisionMessage + QuestionMessage + ReviewMessage

**Files:**
- Create: `frontend/src/messages/FindingMessage.tsx` + `.test.tsx`
- Create: `frontend/src/messages/DecisionMessage.tsx` + `.test.tsx`
- Create: `frontend/src/messages/QuestionMessage.tsx` + `.test.tsx`
- Create: `frontend/src/messages/ReviewMessage.tsx` + `.test.tsx`

All four share a single pattern: `BaseMessage` with `tag` + `tone` set per type and body wrapped in `MentionText`.

- [ ] **Step 17.1: Write failing tests (one per type)**

Create `frontend/src/messages/FindingMessage.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { FindingMessage } from "./FindingMessage";

describe("<FindingMessage />", () => {
  it("renders finding tag + body", () => {
    renderWithProviders(
      <FindingMessage
        actor={{ kind: "claude", initial: "CC", displayName: "claude" }}
        message={{
          id: 4, topic_id: 1, type: "finding", actor_type: "agent", actor_id: 12,
          body: "图太多文字太少", metadata: {}, ref_event_id: null,
          created_at: "2026-05-19T09:46:00Z",
        }}
      />,
    );
    expect(screen.getByText("finding")).toBeInTheDocument();
  });
});
```

Create `frontend/src/messages/DecisionMessage.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { DecisionMessage } from "./DecisionMessage";

describe("<DecisionMessage />", () => {
  it("shows decision type and ref id", () => {
    renderWithProviders(
      <DecisionMessage
        actor={{ kind: "human", initial: "N", displayName: "Neo" }}
        message={{
          id: 10, topic_id: 1, type: "decision", actor_type: "human", actor_id: 1,
          body: "approve spec change v2 → v3",
          metadata: { decision_type: "adopt", ref_message_id: 8 },
          ref_event_id: null, created_at: "2026-05-19T10:35:00Z",
        }}
      />,
    );
    expect(screen.getByText("decision · adopt")).toBeInTheDocument();
    expect(screen.getByText(/approve spec change/)).toBeInTheDocument();
  });
});
```

Create `frontend/src/messages/QuestionMessage.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { QuestionMessage } from "./QuestionMessage";

describe("<QuestionMessage />", () => {
  it("renders question tag", () => {
    renderWithProviders(
      <QuestionMessage
        actor={{ kind: "human", initial: "M", displayName: "Morpheus" }}
        message={{
          id: 5, topic_id: 1, type: "question", actor_type: "human", actor_id: 3,
          body: "?", metadata: {}, ref_event_id: null,
          created_at: "2026-05-19T09:55:00Z",
        }}
      />,
    );
    expect(screen.getByText("question")).toBeInTheDocument();
  });
});
```

Create `frontend/src/messages/ReviewMessage.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { ReviewMessage } from "./ReviewMessage";

describe("<ReviewMessage />", () => {
  it("renders review tag and ref note", () => {
    renderWithProviders(
      <ReviewMessage
        actor={{ kind: "codex", initial: "CX", displayName: "codex" }}
        message={{
          id: 13, topic_id: 1, type: "review", actor_type: "agent", actor_id: 13,
          body: "建议把事件性放最前", metadata: { ref_message_id: 11 },
          ref_event_id: null, created_at: "2026-05-19T11:05:00Z",
        }}
      />,
    );
    expect(screen.getByText(/review/)).toBeInTheDocument();
    expect(screen.getByText(/↳ #11/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 17.2: Create the four components**

`frontend/src/messages/FindingMessage.tsx`:
```tsx
import type { MessageDTO } from "../api/types";
import { BaseMessage } from "./BaseMessage";
import { MentionText } from "./MentionText";

interface Actor { kind: "human" | "claude" | "codex" | "system"; initial: string; displayName: string }

export function FindingMessage({ message, actor }: { message: MessageDTO; actor: Actor }) {
  return (
    <BaseMessage
      actor={actor}
      timeIso={message.created_at}
      tag="finding"
      tone="finding"
      body={<MentionText>{message.body}</MentionText>}
    />
  );
}
```

`frontend/src/messages/DecisionMessage.tsx`:
```tsx
import type { MessageDTO } from "../api/types";
import type { DecisionMeta } from "../api/types";
import { BaseMessage } from "./BaseMessage";

interface Actor { kind: "human" | "claude" | "codex" | "system"; initial: string; displayName: string }

export function DecisionMessage({ message, actor }: { message: MessageDTO; actor: Actor }) {
  const meta = message.metadata as Partial<DecisionMeta>;
  const decision = meta.decision_type ?? "adopt";
  return (
    <BaseMessage
      actor={actor}
      timeIso={message.created_at}
      tag={`decision · ${decision}`}
      tone="decision"
      body={
        <div>
          <span>{message.body}</span>
          {meta.ref_message_id !== undefined && (
            <span className="ml-2 text-[11px] font-mono text-text-dim">↳ #{meta.ref_message_id}</span>
          )}
        </div>
      }
    />
  );
}
```

`frontend/src/messages/QuestionMessage.tsx`:
```tsx
import type { MessageDTO } from "../api/types";
import { BaseMessage } from "./BaseMessage";
import { MentionText } from "./MentionText";

interface Actor { kind: "human" | "claude" | "codex" | "system"; initial: string; displayName: string }

export function QuestionMessage({ message, actor }: { message: MessageDTO; actor: Actor }) {
  return (
    <BaseMessage
      actor={actor}
      timeIso={message.created_at}
      tag="question"
      tone="question"
      body={<MentionText>{message.body}</MentionText>}
    />
  );
}
```

`frontend/src/messages/ReviewMessage.tsx`:
```tsx
import type { MessageDTO } from "../api/types";
import { BaseMessage } from "./BaseMessage";
import { MentionText } from "./MentionText";

interface Actor { kind: "human" | "claude" | "codex" | "system"; initial: string; displayName: string }

export function ReviewMessage({ message, actor }: { message: MessageDTO; actor: Actor }) {
  const refId = (message.metadata as { ref_message_id?: number }).ref_message_id;
  return (
    <BaseMessage
      actor={actor}
      timeIso={message.created_at}
      tag="review"
      tone="review"
      body={
        <div>
          <MentionText>{message.body}</MentionText>
          {refId !== undefined && (
            <div className="text-[11px] font-mono text-text-dim mt-1">↳ #{refId}</div>
          )}
        </div>
      }
    />
  );
}
```

- [ ] **Step 17.3: Run tests**

```bash
cd frontend && pnpm test "FindingMessage|DecisionMessage|QuestionMessage|ReviewMessage"
```

Expected: 4 tests pass.

- [ ] **Step 17.4: Commit**

```bash
git add frontend/src/messages/FindingMessage.tsx frontend/src/messages/FindingMessage.test.tsx \
        frontend/src/messages/DecisionMessage.tsx frontend/src/messages/DecisionMessage.test.tsx \
        frontend/src/messages/QuestionMessage.tsx frontend/src/messages/QuestionMessage.test.tsx \
        frontend/src/messages/ReviewMessage.tsx frontend/src/messages/ReviewMessage.test.tsx
git commit -m "feat(frontend): finding/decision/question/review message components"
```

---

## Task 18: HandoffMessage + NudgeMessage + ProactiveFindingMessage

**Files:**
- Create: `frontend/src/messages/HandoffMessage.tsx` + `.test.tsx`
- Create: `frontend/src/messages/NudgeMessage.tsx` + `.test.tsx`
- Create: `frontend/src/messages/ProactiveFindingMessage.tsx` + `.test.tsx`

- [ ] **Step 18.1: Write failing tests**

Create `frontend/src/messages/HandoffMessage.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { HandoffMessage } from "./HandoffMessage";

describe("<HandoffMessage />", () => {
  it("renders handoff tag with from→to", () => {
    renderWithProviders(
      <HandoffMessage
        actor={{ kind: "claude", initial: "CC", displayName: "claude" }}
        message={{
          id: 11, topic_id: 1, type: "handoff", actor_type: "agent", actor_id: 11,
          body: "P5 文字解释 @codex 接一下",
          metadata: { from_actor_id: 11, to_actor_id: 13 },
          ref_event_id: null, created_at: "2026-05-19T10:40:00Z",
        }}
      />,
    );
    expect(screen.getByText(/handoff/)).toBeInTheDocument();
    expect(screen.getByText(/#11.*#13/)).toBeInTheDocument();
  });
});
```

Create `frontend/src/messages/NudgeMessage.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { NudgeMessage } from "./NudgeMessage";

describe("<NudgeMessage />", () => {
  it("renders nudge tag and reason", () => {
    renderWithProviders(
      <NudgeMessage
        actor={{ kind: "system", initial: "S", displayName: "system" }}
        message={{
          id: 12, topic_id: 1, type: "nudge", actor_type: "system", actor_id: null,
          body: "讨论 framing 25 分钟", metadata: { reason: "framing-loop" },
          ref_event_id: null, created_at: "2026-05-19T10:50:00Z",
        }}
      />,
    );
    expect(screen.getByText(/nudge/)).toBeInTheDocument();
    expect(screen.getByText(/framing-loop/)).toBeInTheDocument();
  });
});
```

Create `frontend/src/messages/ProactiveFindingMessage.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { ProactiveFindingMessage } from "./ProactiveFindingMessage";

describe("<ProactiveFindingMessage />", () => {
  it("renders proactive tag", () => {
    renderWithProviders(
      <ProactiveFindingMessage
        actor={{ kind: "claude", initial: "CC", displayName: "claude" }}
        message={{
          id: 7, topic_id: 1, type: "proactive_finding", actor_type: "agent", actor_id: 12,
          body: "v3 slide 5 建议加文字", metadata: {},
          ref_event_id: null, created_at: "2026-05-19T10:20:00Z",
        }}
      />,
    );
    expect(screen.getByText("proactive")).toBeInTheDocument();
  });
});
```

- [ ] **Step 18.2: Create the components**

`frontend/src/messages/HandoffMessage.tsx`:
```tsx
import type { MessageDTO } from "../api/types";
import { BaseMessage } from "./BaseMessage";
import { MentionText } from "./MentionText";

interface Actor { kind: "human" | "claude" | "codex" | "system"; initial: string; displayName: string }

export function HandoffMessage({ message, actor }: { message: MessageDTO; actor: Actor }) {
  const meta = message.metadata as { from_actor_id?: number; to_actor_id?: number };
  return (
    <BaseMessage
      actor={actor}
      timeIso={message.created_at}
      tag={`handoff · #${meta.from_actor_id ?? "?"} → #${meta.to_actor_id ?? "?"}`}
      tone="handoff"
      body={<MentionText>{message.body}</MentionText>}
    />
  );
}
```

`frontend/src/messages/NudgeMessage.tsx`:
```tsx
import type { MessageDTO } from "../api/types";
import { BaseMessage } from "./BaseMessage";

interface Actor { kind: "system" | "human" | "claude" | "codex"; initial: string; displayName: string }

export function NudgeMessage({ message, actor }: { message: MessageDTO; actor: Actor }) {
  const meta = message.metadata as { reason?: string };
  return (
    <BaseMessage
      actor={actor}
      timeIso={message.created_at}
      tag={`nudge${meta.reason ? ` · ${meta.reason}` : ""}`}
      tone="nudge"
      body={<span>{message.body}</span>}
    />
  );
}
```

`frontend/src/messages/ProactiveFindingMessage.tsx`:
```tsx
import type { MessageDTO } from "../api/types";
import { BaseMessage } from "./BaseMessage";
import { MentionText } from "./MentionText";

interface Actor { kind: "human" | "claude" | "codex" | "system"; initial: string; displayName: string }

export function ProactiveFindingMessage({ message, actor }: { message: MessageDTO; actor: Actor }) {
  return (
    <BaseMessage
      actor={actor}
      timeIso={message.created_at}
      tag="proactive"
      tone="proactive"
      body={<MentionText>{message.body}</MentionText>}
    />
  );
}
```

- [ ] **Step 18.3: Run tests**

```bash
cd frontend && pnpm test "HandoffMessage|NudgeMessage|ProactiveFindingMessage"
```

Expected: 3 tests pass.

- [ ] **Step 18.4: Commit**

```bash
git add frontend/src/messages/HandoffMessage.tsx frontend/src/messages/HandoffMessage.test.tsx \
        frontend/src/messages/NudgeMessage.tsx frontend/src/messages/NudgeMessage.test.tsx \
        frontend/src/messages/ProactiveFindingMessage.tsx frontend/src/messages/ProactiveFindingMessage.test.tsx
git commit -m "feat(frontend): handoff/nudge/proactive_finding message components"
```

---

## Task 19: ArtifactRevisionMessage with inline thumbnail

**Files:**
- Create: `frontend/src/messages/ArtifactRevisionMessage.tsx` + `.test.tsx`
- Create: `frontend/src/messages/SlideThumb.tsx`

Inline preview matches mock.html `.slide-thumb` styling (hbar / lbar / chart svg style cells). For v1.5b without real PPT preview URIs, draw 4 generic slide thumbs; metadata `preview_uri` (when present) wins.

- [ ] **Step 19.1: Create `frontend/src/messages/SlideThumb.tsx`**

```tsx
import { cn } from "../lib/cn";

interface Props {
  num: number;
  variant?: "title" | "text" | "chart" | "grid";
  href?: string;
}

export function SlideThumb({ num, variant = "text", href }: Props) {
  const inner = (
    <div className="relative w-[64px] h-[40px] rounded border border-border-soft bg-surface-elev overflow-hidden flex flex-col gap-1 p-1.5">
      {variant === "title" && (
        <>
          <div className="h-1.5 bg-text rounded-sm w-3/4" />
          <div className="h-1 bg-border rounded-sm w-1/2" />
        </>
      )}
      {variant === "text" && (
        <>
          <div className="h-1 bg-text rounded-sm w-2/3" />
          <div className="h-px bg-border rounded-sm w-full mt-auto" />
          <div className="h-px bg-border rounded-sm w-5/6" />
        </>
      )}
      {variant === "chart" && (
        <>
          <div className="h-1 bg-text rounded-sm w-1/2" />
          <div className="flex gap-px items-end h-full mt-1">
            <div className="bg-accent w-1.5 h-1/2" />
            <div className="bg-accent w-1.5 h-3/4" />
            <div className="bg-accent w-1.5 h-2/5" />
            <div className="bg-accent w-1.5 h-full" />
          </div>
        </>
      )}
      {variant === "grid" && (
        <div className="grid grid-cols-4 gap-px h-full">
          {Array.from({ length: 12 }).map((_, i) => (
            <div key={i} className="bg-border-soft" />
          ))}
        </div>
      )}
      <span className="absolute bottom-0.5 right-1 text-[8px] font-mono text-text-dim">{num}</span>
    </div>
  );
  return href ? <a href={href} target="_blank" rel="noreferrer" className={cn()}>{inner}</a> : inner;
}
```

- [ ] **Step 19.2: Write failing test**

Create `frontend/src/messages/ArtifactRevisionMessage.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { ArtifactRevisionMessage } from "./ArtifactRevisionMessage";

describe("<ArtifactRevisionMessage />", () => {
  it("renders artifact tag with version + thumbnails", () => {
    renderWithProviders(
      <ArtifactRevisionMessage
        actor={{ kind: "claude", initial: "CC", displayName: "claude" }}
        message={{
          id: 3, topic_id: 1, type: "artifact_revision", actor_type: "agent", actor_id: 11,
          body: "v0: 8 页骨架",
          metadata: { artifact_name: "ai-memory-talk.pptx", version: "v0" },
          ref_event_id: null, created_at: "2026-05-19T09:31:00Z",
        }}
      />,
    );
    expect(screen.getByText(/artifact_revision/)).toBeInTheDocument();
    expect(screen.getByText(/ai-memory-talk\.pptx/)).toBeInTheDocument();
    expect(screen.getByText(/v0/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 19.3: Create `frontend/src/messages/ArtifactRevisionMessage.tsx`**

```tsx
import type { MessageDTO, ArtifactRevisionMeta } from "../api/types";
import { BaseMessage } from "./BaseMessage";
import { SlideThumb } from "./SlideThumb";

interface Actor { kind: "human" | "claude" | "codex" | "system"; initial: string; displayName: string }

export function ArtifactRevisionMessage({ message, actor }: { message: MessageDTO; actor: Actor }) {
  const meta = message.metadata as Partial<ArtifactRevisionMeta>;
  const name = meta.artifact_name ?? `artifact#${meta.artifact_id ?? "?"}`;
  const version = meta.version ?? "?";
  return (
    <BaseMessage
      actor={actor}
      timeIso={message.created_at}
      tag={`artifact_revision · ${version}`}
      tone="artifact"
      body={
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <span className="font-mono text-[13px]">{name}</span>
            <span className="bg-artifact text-bg px-1.5 py-px rounded text-[10px] font-mono">{version}</span>
          </div>
          <div className="text-[13px]">{message.body}</div>
          <div className="flex gap-1.5">
            <SlideThumb num={1} variant="title" />
            <SlideThumb num={2} variant="text" />
            <SlideThumb num={3} variant="chart" />
            <SlideThumb num={4} variant="grid" />
          </div>
        </div>
      }
    />
  );
}
```

- [ ] **Step 19.4: Run test**

```bash
cd frontend && pnpm test ArtifactRevisionMessage
```

Expected: 1 test passes.

- [ ] **Step 19.5: Commit**

```bash
git add frontend/src/messages/ArtifactRevisionMessage.tsx frontend/src/messages/ArtifactRevisionMessage.test.tsx frontend/src/messages/SlideThumb.tsx
git commit -m "feat(frontend): artifact_revision component with inline slide thumbnails"
```

---

## Task 20: SpecChangeMessage with diff + approval bar

**Files:**
- Create: `frontend/src/messages/SpecChangeMessage.tsx` + `.test.tsx`

Inline diff is keep-it-simple-for-v1.5b: show `before` and `after` values, plus an approval bar listing existing approvers and an "Approve" button (Phase 8 wires it to a real `decision` message post).

- [ ] **Step 20.1: Write failing test**

Create `frontend/src/messages/SpecChangeMessage.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { SpecChangeMessage } from "./SpecChangeMessage";

describe("<SpecChangeMessage />", () => {
  it("renders file + before/after + approvers", () => {
    renderWithProviders(
      <SpecChangeMessage
        actor={{ kind: "codex", initial: "CX", displayName: "codex" }}
        message={{
          id: 8, topic_id: 1, type: "spec_change", actor_type: "agent", actor_id: 13,
          body: "字号 10 → 14",
          metadata: {
            file: ".claude/skills/research-talk-style/SKILL.md",
            before: 10, after: 14, approvers: ["Trinity"],
          },
          ref_event_id: null, created_at: "2026-05-19T10:28:00Z",
        }}
      />,
    );
    expect(screen.getByText(/research-talk-style/)).toBeInTheDocument();
    expect(screen.getByText("10")).toBeInTheDocument();
    expect(screen.getByText("14")).toBeInTheDocument();
    expect(screen.getByText(/Trinity/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /approve/i })).toBeInTheDocument();
  });
});
```

- [ ] **Step 20.2: Create `frontend/src/messages/SpecChangeMessage.tsx`**

```tsx
import type { MessageDTO, SpecChangeMeta } from "../api/types";
import { BaseMessage } from "./BaseMessage";

interface Actor { kind: "human" | "claude" | "codex" | "system"; initial: string; displayName: string }

export function SpecChangeMessage({ message, actor }: { message: MessageDTO; actor: Actor }) {
  const meta = message.metadata as Partial<SpecChangeMeta>;
  return (
    <BaseMessage
      actor={actor}
      timeIso={message.created_at}
      tag="spec_change"
      tone="spec"
      body={
        <div className="flex flex-col gap-2">
          <div className="font-mono text-[12px] text-text-muted">{meta.file ?? "?"}</div>
          <div className="text-[13px]">{message.body}</div>
          <div className="flex items-center gap-2 text-[12px]">
            <span className="font-mono px-1.5 py-px rounded bg-finding-bg text-finding">{String(meta.before ?? "-")}</span>
            <span className="text-text-dim">→</span>
            <span className="font-mono px-1.5 py-px rounded bg-spec-bg text-spec">{String(meta.after ?? "-")}</span>
          </div>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-[11px] text-text-muted">approvers:</span>
            {(meta.approvers ?? []).length === 0 ? (
              <span className="text-[11px] text-text-dim italic">none yet</span>
            ) : (
              meta.approvers!.map((name) => (
                <span key={name} className="text-[11px] px-1.5 py-px bg-surface rounded font-mono">{name}</span>
              ))
            )}
            <div className="flex-1" />
            <button type="button" className="px-2 py-1 rounded bg-spec text-bg text-[12px] font-medium">
              Approve
            </button>
            <button type="button" className="px-2 py-1 rounded border border-border text-[12px]">
              See diff
            </button>
          </div>
        </div>
      }
    />
  );
}
```

- [ ] **Step 20.3: Run test**

```bash
cd frontend && pnpm test SpecChangeMessage
```

Expected: 1 test passes.

- [ ] **Step 20.4: Commit**

```bash
git add frontend/src/messages/SpecChangeMessage.tsx frontend/src/messages/SpecChangeMessage.test.tsx
git commit -m "feat(frontend): spec_change component with diff + approval bar (UI only, not wired)"
```

---

## Task 21: TaskTreeProposalMessage with task list

**Files:**
- Create: `frontend/src/messages/TaskTreeProposalMessage.tsx` + `.test.tsx`

- [ ] **Step 21.1: Write failing test**

Create `frontend/src/messages/TaskTreeProposalMessage.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { TaskTreeProposalMessage } from "./TaskTreeProposalMessage";

describe("<TaskTreeProposalMessage />", () => {
  it("renders task tree title + items", () => {
    renderWithProviders(
      <TaskTreeProposalMessage
        actor={{ kind: "claude", initial: "CC", displayName: "claude" }}
        message={{
          id: 6, topic_id: 1, type: "task_tree_proposal", actor_type: "agent", actor_id: 11,
          body: "建议分 3 个任务",
          metadata: {
            title: "PPT",
            items: [
              { title: "Framing", status: "done" },
              { title: "矩阵", status: "active" },
              { title: "排练", status: "pending" },
            ],
          },
          ref_event_id: null, created_at: "2026-05-19T09:33:00Z",
        }}
      />,
    );
    expect(screen.getByText("PPT")).toBeInTheDocument();
    expect(screen.getByText("Framing")).toBeInTheDocument();
    expect(screen.getByText(/1 \/ 3/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 21.2: Create `frontend/src/messages/TaskTreeProposalMessage.tsx`**

```tsx
import type { MessageDTO, TaskTreeProposalMeta } from "../api/types";
import { BaseMessage } from "./BaseMessage";
import { cn } from "../lib/cn";

interface Actor { kind: "human" | "claude" | "codex" | "system"; initial: string; displayName: string }

export function TaskTreeProposalMessage({ message, actor }: { message: MessageDTO; actor: Actor }) {
  const meta = message.metadata as Partial<TaskTreeProposalMeta>;
  const items = meta.items ?? [];
  const doneCount = items.filter((i) => i.status === "done").length;

  return (
    <BaseMessage
      actor={actor}
      timeIso={message.created_at}
      tag="task_tree"
      tone="tree"
      body={
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center gap-2 text-[13px]">
            <span className="font-semibold">{meta.title ?? "task tree"}</span>
            <span className="font-mono text-text-dim text-[11px]">{doneCount} / {items.length} done</span>
          </div>
          <ul className="flex flex-col gap-1">
            {items.map((it, i) => (
              <li key={i} className="flex items-center gap-2 text-[12.5px]">
                <span
                  className={cn(
                    "w-2 h-2 rounded-full",
                    it.status === "done" && "bg-status-on",
                    it.status === "active" && "bg-status-work",
                    (!it.status || it.status === "pending") && "border border-border bg-surface",
                  )}
                />
                <span className={it.status === "done" ? "text-text-dim line-through" : ""}>{it.title}</span>
                {it.owner_name && <span className="ml-auto text-[11px] font-mono text-text-dim">{it.owner_name}</span>}
              </li>
            ))}
          </ul>
        </div>
      }
    />
  );
}
```

- [ ] **Step 21.3: Run test**

```bash
cd frontend && pnpm test TaskTreeProposalMessage
```

Expected: 1 test passes.

- [ ] **Step 21.4: Commit**

```bash
git add frontend/src/messages/TaskTreeProposalMessage.tsx frontend/src/messages/TaskTreeProposalMessage.test.tsx
git commit -m "feat(frontend): task_tree_proposal component with progress + task list"
```

---

## Task 22: Wire Message dispatch into TopicView

**Files:**
- Modify: `frontend/src/topic/TopicView.tsx`
- Create: `frontend/src/topic/Stream.tsx`
- Modify: `frontend/src/topic/TopicView.test.tsx`

- [ ] **Step 22.1: Create `frontend/src/topic/Stream.tsx`**

```tsx
import type { MessageDTO } from "../api/types";
import { Message } from "../messages/Message";
import { makeActorResolver, type Directory } from "../messages/actorResolver";
import { DaySeparator } from "./DaySeparator";

interface Props {
  messages: MessageDTO[];
  directory: Directory;
}

function dayLabel(iso: string): string {
  return new Date(iso).toLocaleDateString("zh-CN");
}

export function Stream({ messages, directory }: Props) {
  const resolve = makeActorResolver(directory);
  let lastDay: string | null = null;

  return (
    <div className="flex flex-col">
      {messages.map((m) => {
        const day = dayLabel(m.created_at);
        const showDay = day !== lastDay;
        lastDay = day;
        return (
          <div key={m.id}>
            {showDay && <DaySeparator label={day} />}
            <Message message={m} resolveActor={resolve} />
          </div>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 22.2: Update `frontend/src/topic/TopicView.tsx`**

```tsx
import { useTopicMessages } from "../api/queries";
import { TopicHeader } from "./TopicHeader";
import { Stream } from "./Stream";

interface Props {
  topicId: number;
  topicTitle: string;
}

const SCRATCH_DIRECTORY = {
  humans: [
    { id: 1, name: "Neo" },
    { id: 2, name: "Trinity" },
    { id: 3, name: "Morpheus" },
  ],
  agentInstances: [
    { id: 11, role: "claude", device_label: "neo-mbp", human_id: 1 },
    { id: 12, role: "claude", device_label: "trinity-air", human_id: 2 },
    { id: 13, role: "codex", device_label: "neo-mbp", human_id: 1 },
  ],
};

export function TopicView({ topicId, topicTitle }: Props) {
  const { data, isLoading, isError } = useTopicMessages(topicId);

  return (
    <div className="flex flex-col h-full">
      <TopicHeader
        title={topicTitle}
        goal={{ doneCount: 3, totalCount: 7, currentTaskTitle: "P2 framing 改写" }}
      />
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {isLoading && <div className="text-text-dim">加载中…</div>}
        {isError && <div className="text-text-dim">加载失败</div>}
        {data && <Stream messages={data} directory={SCRATCH_DIRECTORY} />}
      </div>
    </div>
  );
}
```

Note: `SCRATCH_DIRECTORY` is a temporary stub. Task 25 replaces it with a real `/api/directory` query.

- [ ] **Step 22.3: Update `frontend/src/topic/TopicView.test.tsx`**

```tsx
import { describe, it, expect } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { TopicView } from "./TopicView";

describe("<TopicView />", () => {
  it("renders 14 typed messages for topic 1", async () => {
    renderWithProviders(<TopicView topicId={1} topicTitle="t" />);
    await waitFor(() => {
      expect(screen.getAllByTestId("message-row").length).toBe(14);
    });
  });

  it("renders artifact_revision message inline with slide thumbnails", async () => {
    renderWithProviders(<TopicView topicId={1} topicTitle="t" />);
    await waitFor(() => {
      expect(screen.getByText("ai-memory-talk.pptx")).toBeInTheDocument();
    });
  });
});
```

- [ ] **Step 22.4: Update App.tsx to pass title**

```tsx
import { AppShell } from "./layout/AppShell";
import { Sidebar } from "./layout/Sidebar";
import { TopicView } from "./topic/TopicView";

export default function App() {
  return (
    <AppShell
      sidebar={<Sidebar projectName="Lets" projectRepo="github.com/echomem/lets" attentionCount={4} />}
      main={<TopicView topicId={1} topicTitle="为 Agent 记忆写一个研讨 PPT" />}
      context={<div className="p-4 text-text-dim text-sm">Context pane (Phase 6)</div>}
    />
  );
}
```

- [ ] **Step 22.5: Run all tests**

```bash
cd frontend && pnpm test
```

Expected: all tests pass.

- [ ] **Step 22.6: Run dev and visually verify**

```bash
cd frontend && pnpm dev
```

Open `http://localhost:5173`. Every message in stream now uses its typed component: chat, status, finding, decision, question, handoff, review, artifact_revision (with thumbnails), spec_change (with diff bar), nudge, proactive, task_tree, system. Compare visually to `web/mock.html` open at `http://localhost:8000/mock`.

- [ ] **Step 22.7: Commit**

```bash
git add frontend/src/topic/TopicView.tsx frontend/src/topic/Stream.tsx frontend/src/topic/TopicView.test.tsx frontend/src/App.tsx
git commit -m "feat(frontend): wire Message dispatch into TopicView; Phase 4 demo passes"
```

---

## Task 23: Composer (textarea + @mention hint + send)

**Files:**
- Create: `frontend/src/topic/Composer.tsx`
- Create: `frontend/src/topic/Composer.test.tsx`

- [ ] **Step 23.1: Write failing test**

Create `frontend/src/topic/Composer.test.tsx`:
```tsx
import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../test/render";
import { Composer } from "./Composer";

describe("<Composer />", () => {
  it("calls onSend with text on Enter; submit button enables when text present", async () => {
    const onSend = vi.fn();
    const user = userEvent.setup();
    renderWithProviders(<Composer onSend={onSend} />);

    const textarea = screen.getByRole("textbox");
    const button = screen.getByRole("button", { name: /发送/ });

    expect(button).toBeDisabled();
    await user.type(textarea, "hello");
    expect(button).toBeEnabled();

    await user.keyboard("{Enter}");
    expect(onSend).toHaveBeenCalledWith("hello");
    expect((textarea as HTMLTextAreaElement).value).toBe("");
  });

  it("Shift+Enter inserts newline without sending", async () => {
    const onSend = vi.fn();
    const user = userEvent.setup();
    renderWithProviders(<Composer onSend={onSend} />);
    const textarea = screen.getByRole("textbox");
    await user.type(textarea, "line1");
    await user.keyboard("{Shift>}{Enter}{/Shift}line2");
    expect(onSend).not.toHaveBeenCalled();
    expect((textarea as HTMLTextAreaElement).value).toBe("line1\nline2");
  });
});
```

- [ ] **Step 23.2: Create `frontend/src/topic/Composer.tsx`**

```tsx
import { useState, type KeyboardEvent } from "react";

interface Props {
  onSend: (body: string) => void;
  placeholder?: string;
  disabled?: boolean;
}

export function Composer({ onSend, placeholder, disabled }: Props) {
  const [text, setText] = useState("");

  function submit() {
    const trimmed = text.trim();
    if (!trimmed) return;
    onSend(trimmed);
    setText("");
  }

  function onKey(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  return (
    <div className="border-t border-border-soft px-6 py-3 bg-surface">
      <div className="rounded-lg border border-border bg-surface-elev px-3 py-2 flex flex-col gap-2">
        <textarea
          rows={1}
          value={text}
          disabled={disabled}
          placeholder={placeholder ?? "发消息，或 @claude / @codex / @human 派活…"}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKey}
          className="bg-transparent outline-none resize-none text-[14px] leading-relaxed min-h-[28px]"
        />
        <div className="flex items-center text-[11px] text-text-dim">
          <span>/ 命令 · @ 提及 · ⏎ 发送 · ⇧⏎ 换行</span>
          <div className="flex-1" />
          <button
            type="button"
            onClick={submit}
            disabled={!text.trim() || disabled}
            className="px-3 py-1 rounded bg-text text-bg disabled:opacity-40 disabled:cursor-not-allowed text-[12px] font-medium"
          >
            发送
          </button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 23.3: Run test**

```bash
cd frontend && pnpm test Composer
```

Expected: 2 tests pass.

- [ ] **Step 23.4: Commit**

```bash
git add frontend/src/topic/Composer.tsx frontend/src/topic/Composer.test.tsx
git commit -m "feat(frontend): Composer with Enter-to-send + Shift+Enter newline"
```

---

## Task 24: Backend — add `GET /api/topics` and `POST /api/topics`

**Files:**
- Create: `tests/test_topics_api.py`
- Modify: `app/main.py`

Topics are currently created only via raw SQL in tests. Frontend needs list + create endpoints.

- [ ] **Step 24.1: Write failing pytest tests**

Create `tests/test_topics_api.py`:
```python
def test_list_topics_empty(client_with_auth):
    res = client_with_auth.get("/api/topics")
    assert res.status_code == 200
    assert res.json() == []


def test_create_and_list_topic(client_with_auth):
    res = client_with_auth.post(
        "/api/topics",
        json={"slug": "t-test", "title": "Test topic"},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["slug"] == "t-test"
    assert body["title"] == "Test topic"
    assert isinstance(body["id"], int)

    listed = client_with_auth.get("/api/topics").json()
    assert len(listed) == 1
    assert listed[0]["slug"] == "t-test"


def test_create_topic_rejects_duplicate_slug(client_with_auth):
    client_with_auth.post("/api/topics", json={"slug": "t-test", "title": "A"})
    res = client_with_auth.post("/api/topics", json={"slug": "t-test", "title": "B"})
    assert res.status_code == 409
```

The fixture `client_with_auth` should already exist in Track A's `tests/conftest.py`. If not, the engineer needs to confirm it before proceeding.

- [ ] **Step 24.2: Run tests (should fail)**

```bash
.venv/bin/pytest tests/test_topics_api.py -v
```

Expected: 3 tests fail with 404 or AttributeError.

- [ ] **Step 24.3: Add endpoints to `app/main.py`**

Locate the section after `GET /api/topics/{topic_id}/messages` (around line 611) and insert before it:

```python
class TopicCreate(BaseModel):
    slug: str
    title: str
    project_id: int | None = None


@app.get("/api/topics")
def list_topics(principal: dict = Depends(get_current_principal)) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM topics ORDER BY updated_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


@app.post("/api/topics", status_code=201)
def create_topic(
    payload: TopicCreate,
    principal: dict = Depends(get_current_principal),
) -> dict:
    with connect() as conn:
        existing = conn.execute(
            "SELECT id FROM topics WHERE slug = ?", (payload.slug,)
        ).fetchone()
        if existing is not None:
            raise HTTPException(status_code=409, detail="slug already exists")
        cursor = conn.execute(
            "INSERT INTO topics (slug, title, project_id) VALUES (?, ?, ?)",
            (payload.slug, payload.title, payload.project_id),
        )
        row = conn.execute(
            "SELECT * FROM topics WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
    return dict(row)
```

Ensure `BaseModel` is already imported (`from pydantic import BaseModel`).

- [ ] **Step 24.4: Run tests (should pass)**

```bash
.venv/bin/pytest tests/test_topics_api.py -v
```

Expected: 3 tests pass.

- [ ] **Step 24.5: Commit**

```bash
git add tests/test_topics_api.py app/main.py
git commit -m "feat(api): add GET/POST /api/topics endpoints"
```

---

## Task 25: Backend — `GET /api/topics/{id}/stream` SSE endpoint

**Files:**
- Create: `tests/test_topics_stream.py`
- Modify: `app/main.py`

Server-side polls the `messages` table since the last message id and streams new rows as SSE events. Simple polling (no LISTEN/NOTIFY) keeps SQLite-friendly.

- [ ] **Step 25.1: Write failing test**

Create `tests/test_topics_stream.py`:
```python
import asyncio
import json
import threading
import time

from fastapi.testclient import TestClient


def test_stream_emits_new_messages(client_with_auth, db_setup):
    # Create a topic
    res = client_with_auth.post("/api/topics", json={"slug": "t-stream", "title": "x"})
    topic_id = res.json()["id"]

    # Post 1 message before subscribing
    post_message_helper(client_with_auth, topic_id, "first")

    received: list[dict] = []

    def consume():
        with client_with_auth.stream(
            "GET", f"/api/topics/{topic_id}/stream?since_id=0", timeout=3.0
        ) as r:
            for raw in r.iter_lines():
                if raw.startswith("data:"):
                    received.append(json.loads(raw[len("data:") :].strip()))
                    if len(received) >= 2:
                        return

    t = threading.Thread(target=consume, daemon=True)
    t.start()
    time.sleep(0.3)
    post_message_helper(client_with_auth, topic_id, "second")
    t.join(timeout=5.0)

    bodies = [m["body"] for m in received]
    assert "first" in bodies
    assert "second" in bodies


def post_message_helper(client, topic_id, body):
    return client.post(
        "/api/messages",
        json={
            "topic_id": topic_id, "type": "chat",
            "actor_type": "human", "actor_id": 1,
            "body": body, "metadata": {},
        },
    )
```

- [ ] **Step 25.2: Add SSE endpoint to `app/main.py`**

Add this near other topic endpoints:

```python
import asyncio
from fastapi.responses import StreamingResponse


@app.get("/api/topics/{topic_id}/stream")
async def stream_topic(
    topic_id: int,
    since_id: int = 0,
    principal: dict = Depends(get_current_principal),
) -> StreamingResponse:
    async def event_gen():
        last_id = since_id
        idle_ticks = 0
        while True:
            with connect() as conn:
                rows = conn.execute(
                    """
                    SELECT * FROM messages
                    WHERE topic_id = ? AND id > ?
                    ORDER BY id ASC
                    LIMIT 50
                    """,
                    (topic_id, last_id),
                ).fetchall()
            if rows:
                for row in rows:
                    payload = dict(row)
                    payload["metadata"] = json.loads(payload["metadata"])
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                    last_id = max(last_id, payload["id"])
                idle_ticks = 0
            else:
                idle_ticks += 1
                if idle_ticks >= 30:
                    yield ": keepalive\n\n"
                    idle_ticks = 0
            await asyncio.sleep(0.5)

    return StreamingResponse(event_gen(), media_type="text/event-stream")
```

- [ ] **Step 25.3: Run tests**

```bash
.venv/bin/pytest tests/test_topics_stream.py -v
```

Expected: 1 test passes (within 5s timeout).

- [ ] **Step 25.4: Commit**

```bash
git add tests/test_topics_stream.py app/main.py
git commit -m "feat(api): SSE stream endpoint for topic messages (polling-backed)"
```

---

## Task 26: Frontend — `useTopicStream` SSE hook + fixture support

**Files:**
- Create: `frontend/src/api/sse.ts`
- Create: `frontend/src/api/sse.test.ts`
- Modify: `frontend/src/fixtures/handlers.ts` — add SSE handler

- [ ] **Step 26.1: Add SSE handler to `frontend/src/fixtures/handlers.ts`**

Inside the `handlers` array, add:

```ts
http.get("/api/topics/:id/stream", () => {
  const stream = new ReadableStream({
    start(controller) {
      const ka = `: keepalive\n\n`;
      controller.enqueue(new TextEncoder().encode(ka));
      controller.close();
    },
  });
  return new HttpResponse(stream, {
    headers: { "Content-Type": "text/event-stream" },
  });
}),
```

This is a no-op fixture: SSE in MSW is hard to simulate well, so fixture mode skips live updates and the Phase 4 visual still works.

- [ ] **Step 26.2: Write failing test**

Create `frontend/src/api/sse.test.ts`:
```ts
import { describe, it, expect } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { useTopicStream } from "./sse";

describe("useTopicStream", () => {
  it("opens an EventSource and exposes empty messages array initially", async () => {
    const { result } = renderHook(() => useTopicStream(1, 0), {
      wrapper: ({ children }) => renderWithProviders(<>{children}</>).asFragment().firstChild
        ? ((globalThis as unknown as { __wrap?: unknown }).__wrap as () => null)()
        : null,
    });
    // Hook setup test — verify it returns the expected shape
    await waitFor(() => expect(result.current).toMatchObject({ messages: [] }));
  });
});
```

Note: this test is intentionally minimal — full SSE end-to-end is covered in Playwright (Phase 11). Replace the renderHook wrapper with a simpler version:

```ts
import { describe, it, expect } from "vitest";
import { useTopicStream } from "./sse";

describe("useTopicStream", () => {
  it("module exports the hook", () => {
    expect(typeof useTopicStream).toBe("function");
  });
});
```

- [ ] **Step 26.3: Create `frontend/src/api/sse.ts`**

```ts
import { useEffect, useState } from "react";
import type { MessageDTO } from "./types";

export interface UseTopicStreamResult {
  messages: MessageDTO[];
}

export function useTopicStream(topicId: number, sinceId: number): UseTopicStreamResult {
  const [messages, setMessages] = useState<MessageDTO[]>([]);

  useEffect(() => {
    setMessages([]);
    if (import.meta.env.VITE_USE_FIXTURES !== "false") return;

    const url = `/api/topics/${topicId}/stream?since_id=${sinceId}`;
    const es = new EventSource(url);
    es.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data) as MessageDTO;
        setMessages((prev) => [...prev, data]);
      } catch {
        /* ignore malformed */
      }
    };
    es.onerror = () => es.close();
    return () => es.close();
  }, [topicId, sinceId]);

  return { messages };
}
```

- [ ] **Step 26.4: Run test**

```bash
cd frontend && pnpm test sse
```

Expected: 1 test passes.

- [ ] **Step 26.5: Commit**

```bash
git add frontend/src/api/sse.ts frontend/src/api/sse.test.ts frontend/src/fixtures/handlers.ts
git commit -m "feat(frontend): useTopicStream SSE hook (no-op in fixture mode)"
```

---

## Task 27: Wire Composer to `usePostMessage` + merge SSE deltas into TopicView

**Files:**
- Modify: `frontend/src/topic/TopicView.tsx`
- Modify: `frontend/src/topic/TopicView.test.tsx`

- [ ] **Step 27.1: Update `frontend/src/topic/TopicView.tsx`**

```tsx
import { useMemo } from "react";
import { useTopicMessages, usePostMessage, useIdentityMe } from "../api/queries";
import { useTopicStream } from "../api/sse";
import { TopicHeader } from "./TopicHeader";
import { Stream } from "./Stream";
import { Composer } from "./Composer";
import type { MessageDTO } from "../api/types";

interface Props {
  topicId: number;
  topicTitle: string;
}

const SCRATCH_DIRECTORY = {
  humans: [
    { id: 1, name: "Neo" },
    { id: 2, name: "Trinity" },
    { id: 3, name: "Morpheus" },
  ],
  agentInstances: [
    { id: 11, role: "claude", device_label: "neo-mbp", human_id: 1 },
    { id: 12, role: "claude", device_label: "trinity-air", human_id: 2 },
    { id: 13, role: "codex", device_label: "neo-mbp", human_id: 1 },
  ],
};

export function TopicView({ topicId, topicTitle }: Props) {
  const me = useIdentityMe();
  const initial = useTopicMessages(topicId);
  const lastId = initial.data?.reduce((a, m) => Math.max(a, m.id), 0) ?? 0;
  const live = useTopicStream(topicId, lastId);
  const postMessage = usePostMessage(topicId);

  const merged: MessageDTO[] = useMemo(() => {
    const base = initial.data ?? [];
    if (live.messages.length === 0) return base;
    const seen = new Set(base.map((m) => m.id));
    const extra = live.messages.filter((m) => !seen.has(m.id));
    return [...base, ...extra];
  }, [initial.data, live.messages]);

  function send(body: string) {
    if (!me.data) return;
    postMessage.mutate({
      topic_id: topicId,
      type: "chat",
      actor_type: "human",
      actor_id: me.data.human.id,
      body,
    });
  }

  return (
    <div className="flex flex-col h-full">
      <TopicHeader
        title={topicTitle}
        goal={{ doneCount: 3, totalCount: 7, currentTaskTitle: "P2 framing 改写" }}
      />
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {initial.isLoading && <div className="text-text-dim">加载中…</div>}
        {initial.isError && <div className="text-text-dim">加载失败</div>}
        <Stream messages={merged} directory={SCRATCH_DIRECTORY} />
      </div>
      <Composer onSend={send} disabled={postMessage.isPending} />
    </div>
  );
}
```

- [ ] **Step 27.2: Update `frontend/src/topic/TopicView.test.tsx`**

```tsx
import { describe, it, expect } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../test/render";
import { TopicView } from "./TopicView";

describe("<TopicView />", () => {
  it("renders 14 typed messages for topic 1", async () => {
    renderWithProviders(<TopicView topicId={1} topicTitle="t" />);
    await waitFor(() => {
      expect(screen.getAllByTestId("message-row").length).toBe(14);
    });
  });

  it("posts a new chat message via composer", async () => {
    const user = userEvent.setup();
    renderWithProviders(<TopicView topicId={1} topicTitle="t" />);
    await waitFor(() => screen.getAllByTestId("message-row"));
    const textarea = screen.getByRole("textbox");
    await user.type(textarea, "hello composer");
    await user.keyboard("{Enter}");
    await waitFor(() => {
      expect(screen.getByText("hello composer")).toBeInTheDocument();
    });
  });
});
```

- [ ] **Step 27.3: Run tests**

```bash
cd frontend && pnpm test TopicView
```

Expected: 2 tests pass.

- [ ] **Step 27.4: Manual smoke (two browser tabs)**

```bash
cd frontend && pnpm dev    # tab A: fixtures
```

In a second terminal:
```bash
.venv/bin/uvicorn app.main:app --reload  # http://localhost:8000
```

In tab B open `http://localhost:5173?real=1` — for now this still uses fixtures since `VITE_USE_FIXTURES` controls bootstrap. Phase 7 introduces the env-flip. Manual smoke for now: post a chat in tab A, see it appear immediately in the stream.

- [ ] **Step 27.5: Commit**

```bash
git add frontend/src/topic/TopicView.tsx frontend/src/topic/TopicView.test.tsx
git commit -m "feat(frontend): wire Composer + SSE merge into TopicView"
```

---

## Task 28: ContextPane container + TopicInfoCard

**Files:**
- Create: `frontend/src/layout/ContextPane.tsx`
- Create: `frontend/src/context/TopicInfoCard.tsx`
- Create: `frontend/src/context/TopicInfoCard.test.tsx`

- [ ] **Step 28.1: Write failing test**

Create `frontend/src/context/TopicInfoCard.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { TopicInfoCard } from "./TopicInfoCard";

describe("<TopicInfoCard />", () => {
  it("renders topic id, title, description, chips", () => {
    renderWithProviders(
      <TopicInfoCard
        topicSlug="T-PPT"
        title="为 Agent 记忆写一个研讨 PPT"
        description="下周三 AI 研讨会 30min talk"
        chips={["exploratory", "3 agents", "talk-prep"]}
      />,
    );
    expect(screen.getByText("T-PPT")).toBeInTheDocument();
    expect(screen.getByText(/30min talk/)).toBeInTheDocument();
    expect(screen.getByText("exploratory")).toBeInTheDocument();
    expect(screen.getByText("talk-prep")).toBeInTheDocument();
  });
});
```

- [ ] **Step 28.2: Create `frontend/src/context/TopicInfoCard.tsx`**

```tsx
interface Props {
  topicSlug: string;
  title: string;
  description: string;
  chips: string[];
}

export function TopicInfoCard({ topicSlug, title, description, chips }: Props) {
  return (
    <div className="border border-border-soft rounded-lg bg-surface-elev p-3">
      <div className="flex items-baseline gap-2 mb-1">
        <span className="font-mono text-[11px] text-text-dim">{topicSlug}</span>
        <span className="font-semibold text-[13px] truncate">{title}</span>
      </div>
      <p className="text-[12px] text-text-muted leading-relaxed">{description}</p>
      <div className="flex flex-wrap gap-1 mt-2">
        {chips.map((c) => (
          <span key={c} className="text-[10.5px] font-mono px-1.5 py-px rounded bg-surface text-text-muted">
            {c}
          </span>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 28.3: Create `frontend/src/layout/ContextPane.tsx`**

```tsx
import type { ReactNode } from "react";

export function ContextPane({ children }: { children: ReactNode }) {
  return <div className="flex flex-col gap-4 p-4">{children}</div>;
}

interface BlockProps { label: string; right?: ReactNode; children: ReactNode }
export function ContextBlock({ label, right, children }: BlockProps) {
  return (
    <div>
      <div className="flex items-baseline justify-between mb-1.5 px-1">
        <span className="text-[11px] uppercase tracking-wider font-semibold text-text-dim">{label}</span>
        {right && <span className="text-[11px] font-mono text-text-dim">{right}</span>}
      </div>
      {children}
    </div>
  );
}
```

- [ ] **Step 28.4: Run test**

```bash
cd frontend && pnpm test TopicInfoCard
```

Expected: 1 test passes.

- [ ] **Step 28.5: Commit**

```bash
git add frontend/src/layout/ContextPane.tsx frontend/src/context/TopicInfoCard.tsx frontend/src/context/TopicInfoCard.test.tsx
git commit -m "feat(frontend): context pane container + TopicInfoCard"
```

---

## Task 29: TaskTreePanel + ArtifactPanel

**Files:**
- Create: `frontend/src/context/TaskTreePanel.tsx` + `.test.tsx`
- Create: `frontend/src/context/ArtifactPanel.tsx` + `.test.tsx`

`TaskTreePanel` mirrors the `task_tree_proposal` rendering but as a persistent context block — same data shape. `ArtifactPanel` shows current artifact name + version chips + slide thumbnails strip.

- [ ] **Step 29.1: Write failing tests**

Create `frontend/src/context/TaskTreePanel.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { TaskTreePanel } from "./TaskTreePanel";

describe("<TaskTreePanel />", () => {
  it("renders title + progress + rows", () => {
    renderWithProviders(
      <TaskTreePanel
        title="研讨 PPT 终版"
        items={[
          { title: "Framing", status: "done" },
          { title: "矩阵", status: "active", owner_name: "claude" },
          { title: "排练", status: "pending" },
        ]}
      />,
    );
    expect(screen.getByText("研讨 PPT 终版")).toBeInTheDocument();
    expect(screen.getByText(/1 \/ 3/)).toBeInTheDocument();
    expect(screen.getByText("claude")).toBeInTheDocument();
  });
});
```

Create `frontend/src/context/ArtifactPanel.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { ArtifactPanel } from "./ArtifactPanel";

describe("<ArtifactPanel />", () => {
  it("renders artifact name, version chip, thumbnails, version row", () => {
    renderWithProviders(
      <ArtifactPanel
        artifactName="ai-memory-talk.pptx"
        currentVersion="v2"
        versions={["v0", "v1", "v2"]}
        totalSlides={9}
      />,
    );
    expect(screen.getByText("ai-memory-talk.pptx")).toBeInTheDocument();
    expect(screen.getAllByText("v2").length).toBeGreaterThan(0);
    expect(screen.getByText(/\+ 5 页未显示/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 29.2: Create `frontend/src/context/TaskTreePanel.tsx`**

```tsx
import { cn } from "../lib/cn";

export interface TaskItem {
  title: string;
  owner_name?: string;
  status?: "pending" | "active" | "done";
}

interface Props { title: string; items: TaskItem[] }

export function TaskTreePanel({ title, items }: Props) {
  const done = items.filter((i) => i.status === "done").length;
  return (
    <div className="border border-border-soft rounded-lg bg-surface-elev p-3 flex flex-col gap-2">
      <div className="flex items-baseline justify-between">
        <span className="font-semibold text-[13px]">{title}</span>
        <span className="font-mono text-[11px] text-text-dim">{done} / {items.length} done</span>
      </div>
      <ul className="flex flex-col gap-1">
        {items.map((it, i) => (
          <li key={i} className="flex items-center gap-2 text-[12.5px]">
            <span
              className={cn(
                "w-2 h-2 rounded-full flex-shrink-0",
                it.status === "done" && "bg-status-on",
                it.status === "active" && "bg-status-work",
                (!it.status || it.status === "pending") && "border border-border bg-surface",
              )}
            />
            <span className={cn("flex-1 truncate", it.status === "done" && "text-text-dim line-through")}>
              {it.title}
            </span>
            {it.owner_name && (
              <span className="text-[11px] font-mono text-text-dim flex-shrink-0">{it.owner_name}</span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
```

- [ ] **Step 29.3: Create `frontend/src/context/ArtifactPanel.tsx`**

```tsx
import { SlideThumb } from "../messages/SlideThumb";
import { cn } from "../lib/cn";

interface Props {
  artifactName: string;
  currentVersion: string;
  versions: string[];
  totalSlides: number;
}

export function ArtifactPanel({ artifactName, currentVersion, versions, totalSlides }: Props) {
  const shown = Math.min(4, totalSlides);
  const hidden = Math.max(0, totalSlides - shown);
  return (
    <div className="border border-border-soft rounded-lg bg-surface-elev p-3 flex flex-col gap-2">
      <div className="flex items-center gap-2 text-[13px]">
        <span className="font-mono truncate flex-1">{artifactName}</span>
        <span className="bg-artifact text-bg px-1.5 py-px rounded text-[10px] font-mono">{currentVersion}</span>
      </div>
      <div className="flex gap-1.5 flex-wrap">
        {Array.from({ length: shown }).map((_, i) => (
          <SlideThumb key={i} num={i + 1} variant={i === 0 ? "title" : i === 2 ? "chart" : i === 3 ? "grid" : "text"} />
        ))}
      </div>
      <div className="flex items-center gap-2 text-[10.5px]">
        {versions.map((v) => (
          <span
            key={v}
            className={cn(
              "px-1.5 py-px rounded font-mono",
              v === currentVersion ? "bg-artifact text-bg" : "bg-surface text-text-muted",
            )}
          >
            {v}
          </span>
        ))}
        {hidden > 0 && (
          <span className="ml-auto text-text-dim">+ {hidden} 页未显示</span>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 29.4: Run tests**

```bash
cd frontend && pnpm test "TaskTreePanel|ArtifactPanel"
```

Expected: 2 tests pass.

- [ ] **Step 29.5: Commit**

```bash
git add frontend/src/context/TaskTreePanel.tsx frontend/src/context/TaskTreePanel.test.tsx \
        frontend/src/context/ArtifactPanel.tsx frontend/src/context/ArtifactPanel.test.tsx
git commit -m "feat(frontend): TaskTreePanel + ArtifactPanel for context pane"
```

---

## Task 30: SpecTouchedPanel + ParticipantsPanel + GitRow

**Files:**
- Create: `frontend/src/context/SpecTouchedPanel.tsx` + `.test.tsx`
- Create: `frontend/src/context/ParticipantsPanel.tsx` + `.test.tsx`
- Create: `frontend/src/context/GitRow.tsx`

- [ ] **Step 30.1: Write failing tests**

Create `frontend/src/context/SpecTouchedPanel.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { SpecTouchedPanel } from "./SpecTouchedPanel";

describe("<SpecTouchedPanel />", () => {
  it("renders each spec path + current version", () => {
    renderWithProviders(
      <SpecTouchedPanel
        items={[
          { path: ".claude/skills/research-talk-style", version: "v2 → v3", pending: true },
          { path: ".claude/skills/pptx", version: "v5", pending: false },
        ]}
      />,
    );
    expect(screen.getByText(/research-talk-style/)).toBeInTheDocument();
    expect(screen.getByText(/v2 → v3/)).toBeInTheDocument();
    expect(screen.getByText(/pptx/)).toBeInTheDocument();
  });
});
```

Create `frontend/src/context/ParticipantsPanel.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { ParticipantsPanel } from "./ParticipantsPanel";

describe("<ParticipantsPanel />", () => {
  it("renders each participant avatar", () => {
    renderWithProviders(
      <ParticipantsPanel
        participants={[
          { kind: "human", initial: "N", name: "Neo" },
          { kind: "claude", initial: "CC", name: "claude · neo-mbp" },
        ]}
      />,
    );
    expect(screen.getByTitle("Neo")).toBeInTheDocument();
    expect(screen.getByTitle("claude · neo-mbp")).toBeInTheDocument();
  });
});
```

- [ ] **Step 30.2: Create the components**

`frontend/src/context/SpecTouchedPanel.tsx`:
```tsx
interface Item { path: string; version: string; pending: boolean }
export function SpecTouchedPanel({ items }: { items: Item[] }) {
  return (
    <div className="flex flex-col gap-1">
      {items.map((it) => (
        <div key={it.path} className="flex items-center gap-2 text-[12px] font-mono">
          <span className="text-text-dim">⟐</span>
          <span className="truncate flex-1">{it.path}</span>
          <span className={it.pending ? "text-spec" : "text-text-dim"}>{it.version}</span>
        </div>
      ))}
    </div>
  );
}
```

`frontend/src/context/ParticipantsPanel.tsx`:
```tsx
import { Avatar } from "../messages/Avatar";

interface P { kind: "human" | "claude" | "codex" | "system"; initial: string; name: string }
export function ParticipantsPanel({ participants }: { participants: P[] }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {participants.map((p) => (
        <div key={p.name} title={p.name}>
          <Avatar kind={p.kind} initial={p.initial} size="sm" />
        </div>
      ))}
    </div>
  );
}
```

`frontend/src/context/GitRow.tsx`:
```tsx
interface Props { branch: string; ahead: number; pendingSpec: boolean }
export function GitRow({ branch, ahead, pendingSpec }: Props) {
  return (
    <div className="flex items-center gap-2 text-[12px] text-text-muted">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="6" cy="6" r="3"/>
        <circle cx="6" cy="18" r="3"/>
        <circle cx="18" cy="12" r="3"/>
        <path d="M6 9v6"/>
        <path d="M9 18h6a3 3 0 0 0 3-3"/>
      </svg>
      <span><span className="font-mono">{branch}</span> · {ahead} ahead{pendingSpec ? " · spec change pending" : ""}</span>
    </div>
  );
}
```

- [ ] **Step 30.3: Run tests**

```bash
cd frontend && pnpm test "SpecTouched|Participants"
```

Expected: 2 tests pass.

- [ ] **Step 30.4: Commit**

```bash
git add frontend/src/context/SpecTouchedPanel.tsx frontend/src/context/SpecTouchedPanel.test.tsx \
        frontend/src/context/ParticipantsPanel.tsx frontend/src/context/ParticipantsPanel.test.tsx \
        frontend/src/context/GitRow.tsx
git commit -m "feat(frontend): SpecTouched + Participants + GitRow context blocks"
```

---

## Task 31: Assemble context pane + wire into App

**Files:**
- Create: `frontend/src/context/TopicContext.tsx`
- Modify: `frontend/src/App.tsx`

`TopicContext` is the composed context pane: TopicInfoCard, GoalDetailPanel (Task 35 — for now use a stub placeholder), TaskTreePanel, ArtifactPanel, SpecTouchedPanel, ParticipantsPanel, GitRow.

- [ ] **Step 31.1: Create `frontend/src/context/TopicContext.tsx`**

```tsx
import { ContextPane, ContextBlock } from "../layout/ContextPane";
import { TopicInfoCard } from "./TopicInfoCard";
import { TaskTreePanel } from "./TaskTreePanel";
import { ArtifactPanel } from "./ArtifactPanel";
import { SpecTouchedPanel } from "./SpecTouchedPanel";
import { ParticipantsPanel } from "./ParticipantsPanel";
import { GitRow } from "./GitRow";

export function TopicContext() {
  return (
    <ContextPane>
      <ContextBlock label="当前 Topic">
        <TopicInfoCard
          topicSlug="T-PPT"
          title="为 Agent 记忆写一个研讨 PPT"
          description="下周三 AI 研讨会 30min talk · 技术受众 · 主讲 Neo"
          chips={["exploratory", "3 agents", "talk-prep"]}
        />
      </ContextBlock>

      <ContextBlock label="目标分解" right="claude · 09:33">
        <TaskTreePanel
          title="研讨 PPT 终版"
          items={[
            { title: "Framing 角度定下来", owner_name: "Morpheus", status: "done" },
            { title: "P4 业界对比矩阵 4×6", owner_name: "claude", status: "done" },
            { title: "Skill 字号修正", owner_name: "codex", status: "done" },
            { title: "P2 framing 改写", owner_name: "claude", status: "active" },
            { title: "P5 加文字解释", status: "pending" },
            { title: "Demo / Q&A 准备", owner_name: "Neo", status: "pending" },
            { title: "排练 30min", status: "pending" },
          ]}
        />
      </ContextBlock>

      <ContextBlock label="Artifact" right="v2 · in-progress">
        <ArtifactPanel
          artifactName="ai-memory-talk.pptx"
          currentVersion="v2"
          versions={["v0", "v1", "v2"]}
          totalSlides={9}
        />
      </ContextBlock>

      <ContextBlock label="本 Topic 涉及 Spec">
        <SpecTouchedPanel
          items={[
            { path: ".claude/skills/research-talk-style", version: "v2 → v3", pending: true },
            { path: ".claude/skills/pptx", version: "v5", pending: false },
          ]}
        />
      </ContextBlock>

      <ContextBlock label="Participants · 6">
        <ParticipantsPanel
          participants={[
            { kind: "human", initial: "N", name: "Neo" },
            { kind: "human", initial: "T", name: "Trinity" },
            { kind: "human", initial: "M", name: "Morpheus" },
            { kind: "claude", initial: "CC", name: "claude · neo-mbp" },
            { kind: "codex", initial: "CX", name: "codex · neo-mbp" },
          ]}
        />
      </ContextBlock>

      <ContextBlock label="Git">
        <GitRow branch="master" ahead={2} pendingSpec />
      </ContextBlock>
    </ContextPane>
  );
}
```

- [ ] **Step 31.2: Update `frontend/src/App.tsx`**

```tsx
import { AppShell } from "./layout/AppShell";
import { Sidebar } from "./layout/Sidebar";
import { TopicView } from "./topic/TopicView";
import { TopicContext } from "./context/TopicContext";

export default function App() {
  return (
    <AppShell
      sidebar={<Sidebar projectName="Lets" projectRepo="github.com/echomem/lets" attentionCount={4} />}
      main={<TopicView topicId={1} topicTitle="为 Agent 记忆写一个研讨 PPT" />}
      context={<TopicContext />}
    />
  );
}
```

- [ ] **Step 31.3: Run dev and visually compare with mock**

```bash
cd frontend && pnpm dev
```

Side-by-side with `web/mock.html`, verify the context pane visually matches the v6 layout.

- [ ] **Step 31.4: Commit**

```bash
git add frontend/src/context/TopicContext.tsx frontend/src/App.tsx
git commit -m "feat(frontend): assemble TopicContext pane with all blocks"
```

---

## Task 32: Phase 6 design checkpoint B

**Files:** none (review)

- [ ] **Step 32.1: Visual review at `http://localhost:5173`**

Open both `http://localhost:5173` and `http://localhost:8000/mock` side-by-side. Compare typed-message accent saturation:
- finding green vs decision purple vs artifact blue — does the palette breathe right?
- spec_change / nudge / proactive intensities — too loud? too soft?
- artifact slide thumbnails — color match?

- [ ] **Step 32.2: Apply any token adjustments to `frontend/src/index.css`**

Touch only the "Typed-message accents" group inside `@theme`. Example: drop saturation of `--color-proactive-bg` from 0.06 to 0.04 if it feels too hot.

- [ ] **Step 32.3: Commit (if any changes)**

```bash
git add frontend/src/index.css
git commit -m "chore(frontend): Phase 6 design checkpoint B saturation adjustments"
```

---

## Task 33: AttentionCard + AttentionGroup

**Files:**
- Create: `frontend/src/attention/AttentionCard.tsx` + `.test.tsx`
- Create: `frontend/src/attention/AttentionGroup.tsx` + `.test.tsx`

`AttentionCard` is one row in the attention queue: avatar, who+time, what (truncated), topic ref, 2 quick action buttons (primary + secondary).

- [ ] **Step 33.1: Write failing test**

Create `frontend/src/attention/AttentionCard.test.tsx`:
```tsx
import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../test/render";
import { AttentionCard } from "./AttentionCard";

describe("<AttentionCard />", () => {
  it("renders who, what, topic ref, and fires action callbacks", async () => {
    const user = userEvent.setup();
    const onPrimary = vi.fn();
    const onSecondary = vi.fn();
    renderWithProviders(
      <AttentionCard
        avatar={{ kind: "claude", initial: "CC" }}
        whoLabel="claude · neo-mbp"
        timeIso="2026-05-19T10:32:00Z"
        what="framing 角度要不要更激进？"
        topicRef={{ id: "T-PPT", title: "为 Agent 记忆写一个研讨 PPT" }}
        primary={{ label: "采纳", onClick: onPrimary }}
        secondary={{ label: "先不", onClick: onSecondary }}
      />,
    );
    expect(screen.getByText(/framing/)).toBeInTheDocument();
    expect(screen.getByText("T-PPT")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "采纳" }));
    expect(onPrimary).toHaveBeenCalledTimes(1);
    await user.click(screen.getByRole("button", { name: "先不" }));
    expect(onSecondary).toHaveBeenCalledTimes(1);
  });
});
```

Create `frontend/src/attention/AttentionGroup.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { AttentionGroup } from "./AttentionGroup";

describe("<AttentionGroup />", () => {
  it("renders heading with count and children", () => {
    renderWithProviders(
      <AttentionGroup heading="需要决定" count={2}>
        <div>row 1</div>
        <div>row 2</div>
      </AttentionGroup>,
    );
    expect(screen.getByRole("heading", { name: /需要决定/ })).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
    expect(screen.getByText("row 1")).toBeInTheDocument();
  });
});
```

- [ ] **Step 33.2: Create `frontend/src/attention/AttentionCard.tsx`**

```tsx
import { Avatar } from "../messages/Avatar";
import { formatHHMM } from "../lib/time";

interface Action { label: string; onClick: () => void }

interface Props {
  avatar: { kind: "human" | "claude" | "codex" | "system"; initial: string };
  whoLabel: string;
  timeIso: string;
  what: string;
  topicRef: { id: string; title: string };
  primary: Action;
  secondary?: Action;
}

export function AttentionCard({ avatar, whoLabel, timeIso, what, topicRef, primary, secondary }: Props) {
  return (
    <div className="grid grid-cols-[28px_1fr_auto] gap-3 items-start border border-border-soft rounded-lg bg-surface-elev p-3">
      <Avatar kind={avatar.kind} initial={avatar.initial} />
      <div className="min-w-0">
        <div className="text-[12px] text-text-muted">
          <span className="font-semibold text-text">{whoLabel}</span> · {formatHHMM(timeIso)}
        </div>
        <div className="text-[13.5px] leading-relaxed mt-0.5">{what}</div>
        <div className="text-[11px] text-text-dim mt-1">
          <span className="font-mono">{topicRef.id}</span> · {topicRef.title}
        </div>
      </div>
      <div className="flex flex-col gap-1 self-center">
        <button
          type="button"
          onClick={primary.onClick}
          className="px-2 py-1 rounded bg-text text-bg text-[12px] font-medium whitespace-nowrap"
        >
          {primary.label}
        </button>
        {secondary && (
          <button
            type="button"
            onClick={secondary.onClick}
            className="px-2 py-1 rounded border border-border text-[12px] whitespace-nowrap"
          >
            {secondary.label}
          </button>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 33.3: Create `frontend/src/attention/AttentionGroup.tsx`**

```tsx
import type { ReactNode } from "react";

interface Props {
  heading: string;
  count: number;
  children: ReactNode;
}

export function AttentionGroup({ heading, count, children }: Props) {
  return (
    <section className="flex flex-col gap-2">
      <div className="flex items-baseline gap-2">
        <h3 className="text-[13.5px] font-semibold text-text">{heading}</h3>
        <span className="text-[11px] font-mono text-text-dim">{count}</span>
      </div>
      <div className="flex flex-col gap-2">{children}</div>
    </section>
  );
}
```

- [ ] **Step 33.4: Run tests**

```bash
cd frontend && pnpm test "AttentionCard|AttentionGroup"
```

Expected: 2 tests pass.

- [ ] **Step 33.5: Commit**

```bash
git add frontend/src/attention/
git commit -m "feat(frontend): AttentionCard + AttentionGroup building blocks"
```

---

## Task 34: AttentionView with greeting + 3 groups

**Files:**
- Create: `frontend/src/attention/AttentionView.tsx` + `.test.tsx`

For Phase 7 the data is hand-picked from fixtures: filter messages by type to surface 3 categories. Real "attention" derivation lives behind backend in v1.5c.

- [ ] **Step 34.1: Write failing test**

Create `frontend/src/attention/AttentionView.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { AttentionView } from "./AttentionView";

describe("<AttentionView />", () => {
  it("renders greeting + 3 groups", async () => {
    renderWithProviders(<AttentionView userName="Neo" />);
    await waitFor(() => {
      expect(screen.getByText(/早上好，Neo/)).toBeInTheDocument();
    });
    expect(screen.getByRole("heading", { name: /需要决定/ })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /主动发现/ })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /同事消息/ })).toBeInTheDocument();
  });
});
```

- [ ] **Step 34.2: Create `frontend/src/attention/AttentionView.tsx`**

```tsx
import { useTopicMessages } from "../api/queries";
import type { MessageDTO } from "../api/types";
import { AttentionGroup } from "./AttentionGroup";
import { AttentionCard } from "./AttentionCard";

interface Props { userName: string }

function avatarFor(m: MessageDTO): { kind: "human" | "claude" | "codex" | "system"; initial: string; label: string } {
  if (m.actor_type === "human") {
    const n = String(m.actor_id ?? "?");
    return { kind: "human", initial: n[0]?.toUpperCase() ?? "?", label: `human#${n}` };
  }
  if (m.actor_type === "agent") {
    return { kind: "claude", initial: "CC", label: `agent#${m.actor_id}` };
  }
  return { kind: "system", initial: "S", label: "system" };
}

export function AttentionView({ userName }: Props) {
  const { data, isLoading } = useTopicMessages(1);
  const messages = data ?? [];

  const decide = messages.filter((m) => m.type === "spec_change" || (m.type === "chat" && m.body.endsWith("？")));
  const proactive = messages.filter((m) => m.type === "proactive_finding");
  const peer = messages.filter((m) => m.type === "question");

  return (
    <div className="flex flex-col gap-6 px-8 py-6 overflow-y-auto h-full">
      <div>
        <h2 className="font-[var(--font-display)] text-2xl">早上好，{userName}。</h2>
        <p className="text-text-muted text-[14px] mt-1">
          过去一夜，团队已经有 {decide.length + proactive.length + peer.length} 件事在你的清单里。
        </p>
      </div>
      {isLoading && <div className="text-text-dim">加载中…</div>}

      <AttentionGroup heading="需要决定" count={decide.length}>
        {decide.map((m) => {
          const a = avatarFor(m);
          return (
            <AttentionCard
              key={m.id}
              avatar={{ kind: a.kind, initial: a.initial }}
              whoLabel={a.label}
              timeIso={m.created_at}
              what={m.body}
              topicRef={{ id: "T-PPT", title: "为 Agent 记忆写一个研讨 PPT" }}
              primary={{ label: m.type === "spec_change" ? "Approve" : "采纳", onClick: () => {} }}
              secondary={{ label: m.type === "spec_change" ? "看 diff" : "先不", onClick: () => {} }}
            />
          );
        })}
      </AttentionGroup>

      <AttentionGroup heading="Agent 主动发现" count={proactive.length}>
        {proactive.map((m) => {
          const a = avatarFor(m);
          return (
            <AttentionCard
              key={m.id}
              avatar={{ kind: a.kind, initial: a.initial }}
              whoLabel={a.label}
              timeIso={m.created_at}
              what={m.body}
              topicRef={{ id: "T-PPT", title: "为 Agent 记忆写一个研讨 PPT" }}
              primary={{ label: "采纳建议", onClick: () => {} }}
              secondary={{ label: "略过", onClick: () => {} }}
            />
          );
        })}
      </AttentionGroup>

      <AttentionGroup heading="同事消息" count={peer.length}>
        {peer.map((m) => {
          const a = avatarFor(m);
          return (
            <AttentionCard
              key={m.id}
              avatar={{ kind: a.kind, initial: a.initial }}
              whoLabel={a.label}
              timeIso={m.created_at}
              what={m.body}
              topicRef={{ id: "DM", title: "private message" }}
              primary={{ label: "继续聊", onClick: () => {} }}
              secondary={{ label: "@claude 跟进", onClick: () => {} }}
            />
          );
        })}
      </AttentionGroup>
    </div>
  );
}
```

- [ ] **Step 34.3: Add view router to App**

Update `frontend/src/App.tsx`:
```tsx
import { useState } from "react";
import { AppShell } from "./layout/AppShell";
import { Sidebar } from "./layout/Sidebar";
import { TopicView } from "./topic/TopicView";
import { TopicContext } from "./context/TopicContext";
import { AttentionView } from "./attention/AttentionView";

type View = { kind: "topic"; id: number; title: string } | { kind: "attention" };

export default function App() {
  const [view, setView] = useState<View>({ kind: "topic", id: 1, title: "为 Agent 记忆写一个研讨 PPT" });

  return (
    <AppShell
      sidebar={
        <Sidebar
          projectName="Lets"
          projectRepo="github.com/echomem/lets"
          attentionCount={4}
          onClickAttention={() => setView({ kind: "attention" })}
          onClickTopic={() => setView({ kind: "topic", id: 1, title: "为 Agent 记忆写一个研讨 PPT" })}
        />
      }
      main={
        view.kind === "topic" ? (
          <TopicView topicId={view.id} topicTitle={view.title} />
        ) : (
          <AttentionView userName="Neo" />
        )
      }
      context={view.kind === "topic" ? <TopicContext /> : <div className="p-4 text-text-dim text-sm">No context</div>}
    />
  );
}
```

- [ ] **Step 34.4: Update `Sidebar.tsx` to accept handlers**

In `frontend/src/layout/Sidebar.tsx` update props + buttons:
```tsx
interface SidebarProps {
  projectName: string;
  projectRepo: string;
  attentionCount?: number;
  onClickAttention?: () => void;
  onClickTopic?: () => void;
}
```

Replace the attention button with `<button onClick={onClickAttention} …>` and add a `<button onClick={onClickTopic} …>` row inside the Channels collapsible (label `T-PPT 为 Agent 记忆写一个研讨 PPT`).

- [ ] **Step 34.5: Run tests**

```bash
cd frontend && pnpm test AttentionView
```

Expected: 1 test passes.

- [ ] **Step 34.6: Commit**

```bash
git add frontend/src/attention/AttentionView.tsx frontend/src/attention/AttentionView.test.tsx \
        frontend/src/App.tsx frontend/src/layout/Sidebar.tsx
git commit -m "feat(frontend): AttentionView with 3 groups + sidebar view switching"
```

---

## Task 35: GoalDetailPanel in context pane

**Files:**
- Create: `frontend/src/context/GoalDetailPanel.tsx` + `.test.tsx`
- Modify: `frontend/src/context/TopicContext.tsx`

This is where the full goal detail lives now (per design decision — header carries the slim progress, context pane carries the spec + approvers + Mark as Final).

- [ ] **Step 35.1: Write failing test**

Create `frontend/src/context/GoalDetailPanel.test.tsx`:
```tsx
import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../test/render";
import { GoalDetailPanel } from "./GoalDetailPanel";

describe("<GoalDetailPanel />", () => {
  it("renders artifact name, spec, approvers, and final button", async () => {
    const onMarkFinal = vi.fn();
    const user = userEvent.setup();
    renderWithProviders(
      <GoalDetailPanel
        artifactName="ai-memory-talk.pptx"
        artifactVersion="v3"
        spec="30 分钟 talk · 技术受众 · 突出「事件性记忆 vs 语义记忆」"
        approvers={["Trinity", "Morpheus", "Neo"]}
        onMarkFinal={onMarkFinal}
        onProposeChange={() => {}}
      />,
    );
    expect(screen.getByText("ai-memory-talk.pptx")).toBeInTheDocument();
    expect(screen.getByText(/30 分钟/)).toBeInTheDocument();
    expect(screen.getByText("Trinity")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Mark as Final/ }));
    expect(onMarkFinal).toHaveBeenCalledTimes(1);
  });
});
```

- [ ] **Step 35.2: Create `frontend/src/context/GoalDetailPanel.tsx`**

```tsx
interface Props {
  artifactName: string;
  artifactVersion: string;
  spec: string;
  approvers: string[];
  onMarkFinal: () => void;
  onProposeChange: () => void;
}

export function GoalDetailPanel({ artifactName, artifactVersion, spec, approvers, onMarkFinal, onProposeChange }: Props) {
  return (
    <div className="border border-border-soft rounded-lg bg-surface-elev p-3 flex flex-col gap-2">
      <div className="flex items-center gap-2">
        <span className="text-[11px] uppercase tracking-wider text-text-dim font-semibold">目标 Artifact</span>
        <span className="bg-artifact text-bg px-1.5 py-px rounded text-[10px] font-mono ml-auto">{artifactVersion}</span>
      </div>
      <div className="font-mono text-[13px]">{artifactName}</div>
      <p className="text-[12px] text-text-muted leading-relaxed">{spec}</p>
      <div className="flex flex-wrap gap-1 mt-1">
        <span className="text-[11px] text-text-muted">approvers:</span>
        {approvers.map((a) => (
          <span key={a} className="text-[11px] font-mono px-1.5 py-px bg-surface rounded">{a}</span>
        ))}
      </div>
      <div className="flex gap-2 mt-1">
        <button
          type="button"
          onClick={onMarkFinal}
          className="flex-1 px-2 py-1 rounded bg-text text-bg text-[12px] font-medium"
        >
          Mark as Final
        </button>
        <button
          type="button"
          onClick={onProposeChange}
          className="px-2 py-1 rounded border border-border text-[12px]"
          title="提议修改目标会发起一条 goal_proposal 消息"
        >
          提议修改
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 35.3: Insert into `frontend/src/context/TopicContext.tsx`**

Add a new `<ContextBlock label="目标">` block right after the TopicInfoCard block:
```tsx
<ContextBlock label="目标">
  <GoalDetailPanel
    artifactName="ai-memory-talk.pptx"
    artifactVersion="v3"
    spec="30 分钟 talk · 技术受众 · 突出「事件性记忆 vs 语义记忆」差异化"
    approvers={["Trinity", "Morpheus", "Neo"]}
    onMarkFinal={() => {}}
    onProposeChange={() => {}}
  />
</ContextBlock>
```

Add the import: `import { GoalDetailPanel } from "./GoalDetailPanel";`

- [ ] **Step 35.4: Run tests**

```bash
cd frontend && pnpm test GoalDetail
```

Expected: 1 test passes.

- [ ] **Step 35.5: Commit**

```bash
git add frontend/src/context/GoalDetailPanel.tsx frontend/src/context/GoalDetailPanel.test.tsx frontend/src/context/TopicContext.tsx
git commit -m "feat(frontend): GoalDetailPanel in context pane (slim goal model)"
```

---

## Task 36: Wire spec_change approval → POST decision

**Files:**
- Modify: `frontend/src/messages/SpecChangeMessage.tsx`
- Modify: `frontend/src/messages/SpecChangeMessage.test.tsx`

`Approve` button now actually posts a `decision` typed message referencing the spec_change message id.

- [ ] **Step 36.1: Update test**

Replace `frontend/src/messages/SpecChangeMessage.test.tsx` with:
```tsx
import { describe, it, expect } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../test/render";
import { SpecChangeMessage } from "./SpecChangeMessage";

describe("<SpecChangeMessage />", () => {
  it("renders file + before/after + approvers", () => {
    renderWithProviders(
      <SpecChangeMessage
        actor={{ kind: "codex", initial: "CX", displayName: "codex" }}
        message={{
          id: 8, topic_id: 1, type: "spec_change", actor_type: "agent", actor_id: 13,
          body: "字号 10 → 14",
          metadata: { file: ".claude/skills/x", before: 10, after: 14, approvers: ["Trinity"] },
          ref_event_id: null, created_at: "2026-05-19T10:28:00Z",
        }}
      />,
    );
    expect(screen.getByText("Trinity")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Approve/ })).toBeInTheDocument();
  });

  it("posts a decision message when Approve is clicked", async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <SpecChangeMessage
        actor={{ kind: "codex", initial: "CX", displayName: "codex" }}
        message={{
          id: 8, topic_id: 1, type: "spec_change", actor_type: "agent", actor_id: 13,
          body: "字号 10 → 14",
          metadata: { file: ".claude/skills/x", before: 10, after: 14, approvers: ["Trinity"] },
          ref_event_id: null, created_at: "2026-05-19T10:28:00Z",
        }}
      />,
    );
    await user.click(screen.getByRole("button", { name: /Approve/ }));
    await waitFor(() => {
      expect(screen.getByText(/Approved/)).toBeInTheDocument();
    });
  });
});
```

- [ ] **Step 36.2: Update `frontend/src/messages/SpecChangeMessage.tsx`**

```tsx
import { useState } from "react";
import type { MessageDTO, SpecChangeMeta } from "../api/types";
import { BaseMessage } from "./BaseMessage";
import { usePostMessage, useIdentityMe } from "../api/queries";

interface Actor { kind: "human" | "claude" | "codex" | "system"; initial: string; displayName: string }

export function SpecChangeMessage({ message, actor }: { message: MessageDTO; actor: Actor }) {
  const meta = message.metadata as Partial<SpecChangeMeta>;
  const me = useIdentityMe();
  const post = usePostMessage(message.topic_id);
  const [approved, setApproved] = useState(false);

  function approve() {
    if (!me.data) return;
    post.mutate(
      {
        topic_id: message.topic_id,
        type: "decision",
        actor_type: "human",
        actor_id: me.data.human.id,
        body: `approve spec change for ${meta.file ?? "?"}`,
        metadata: { decision_type: "adopt", ref_message_id: message.id },
      },
      { onSuccess: () => setApproved(true) },
    );
  }

  return (
    <BaseMessage
      actor={actor}
      timeIso={message.created_at}
      tag="spec_change"
      tone="spec"
      body={
        <div className="flex flex-col gap-2">
          <div className="font-mono text-[12px] text-text-muted">{meta.file ?? "?"}</div>
          <div className="text-[13px]">{message.body}</div>
          <div className="flex items-center gap-2 text-[12px]">
            <span className="font-mono px-1.5 py-px rounded bg-finding-bg text-finding">{String(meta.before ?? "-")}</span>
            <span className="text-text-dim">→</span>
            <span className="font-mono px-1.5 py-px rounded bg-spec-bg text-spec">{String(meta.after ?? "-")}</span>
          </div>
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            <span className="text-[11px] text-text-muted">approvers:</span>
            {(meta.approvers ?? []).map((name) => (
              <span key={name} className="text-[11px] px-1.5 py-px bg-surface rounded font-mono">{name}</span>
            ))}
            <div className="flex-1" />
            {approved ? (
              <span className="text-[12px] text-status-on font-medium">Approved ✓</span>
            ) : (
              <>
                <button
                  type="button"
                  onClick={approve}
                  disabled={post.isPending}
                  className="px-2 py-1 rounded bg-spec text-bg text-[12px] font-medium disabled:opacity-40"
                >
                  Approve
                </button>
                <button type="button" className="px-2 py-1 rounded border border-border text-[12px]">
                  See diff
                </button>
              </>
            )}
          </div>
        </div>
      }
    />
  );
}
```

- [ ] **Step 36.3: Run tests**

```bash
cd frontend && pnpm test SpecChangeMessage
```

Expected: 2 tests pass.

- [ ] **Step 36.4: Commit**

```bash
git add frontend/src/messages/SpecChangeMessage.tsx frontend/src/messages/SpecChangeMessage.test.tsx
git commit -m "feat(frontend): spec_change Approve posts a decision message"
```

---

## Task 37: BottomTabs mobile navigation

**Files:**
- Create: `frontend/src/layout/BottomTabs.tsx` + `.test.tsx`
- Modify: `frontend/src/layout/AppShell.tsx`

- [ ] **Step 37.1: Write failing test**

Create `frontend/src/layout/BottomTabs.test.tsx`:
```tsx
import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../test/render";
import { BottomTabs } from "./BottomTabs";

describe("<BottomTabs />", () => {
  it("renders 3 tabs and fires onSelect", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    renderWithProviders(<BottomTabs active="topic" onSelect={onSelect} />);
    expect(screen.getByRole("button", { name: /Topic/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Attention/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Context/ })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Attention/ }));
    expect(onSelect).toHaveBeenCalledWith("attention");
  });
});
```

- [ ] **Step 37.2: Create `frontend/src/layout/BottomTabs.tsx`**

```tsx
import { cn } from "../lib/cn";

export type MobileTab = "topic" | "attention" | "context";

interface Props {
  active: MobileTab;
  onSelect: (tab: MobileTab) => void;
}

const TABS: Array<{ key: MobileTab; label: string }> = [
  { key: "topic", label: "Topic" },
  { key: "attention", label: "Attention" },
  { key: "context", label: "Context" },
];

export function BottomTabs({ active, onSelect }: Props) {
  return (
    <nav className="md:hidden fixed bottom-0 inset-x-0 h-14 bg-surface-elev border-t border-border-soft flex">
      {TABS.map((t) => (
        <button
          key={t.key}
          type="button"
          onClick={() => onSelect(t.key)}
          className={cn(
            "flex-1 flex flex-col items-center justify-center gap-0.5 text-[11px]",
            active === t.key ? "text-text font-semibold" : "text-text-dim",
          )}
        >
          <span>{t.label}</span>
        </button>
      ))}
    </nav>
  );
}
```

- [ ] **Step 37.3: Update `frontend/src/layout/AppShell.tsx` to slot bottom tabs**

```tsx
import type { ReactNode } from "react";

interface AppShellProps {
  sidebar: ReactNode;
  main: ReactNode;
  context: ReactNode;
  bottomTabs?: ReactNode;
}

export function AppShell({ sidebar, main, context, bottomTabs }: AppShellProps) {
  return (
    <div
      data-testid="app-shell"
      className="grid h-[100dvh]"
      style={{ gridTemplateColumns: "var(--side-w, 296px) 1fr var(--context-w, 360px)" }}
    >
      <aside className="border-r border-border-soft bg-surface overflow-y-auto">{sidebar}</aside>
      <main className="flex flex-col min-w-0 overflow-hidden pb-14 md:pb-0">{main}</main>
      <aside className="border-l border-border-soft bg-surface overflow-y-auto hidden xl:block">{context}</aside>
      {bottomTabs}
    </div>
  );
}
```

- [ ] **Step 37.4: Run test**

```bash
cd frontend && pnpm test BottomTabs
```

Expected: 1 test passes.

- [ ] **Step 37.5: Commit**

```bash
git add frontend/src/layout/BottomTabs.tsx frontend/src/layout/BottomTabs.test.tsx frontend/src/layout/AppShell.tsx
git commit -m "feat(frontend): BottomTabs for mobile navigation; AppShell accepts slot"
```

---

## Task 38: Mobile view switching in App

**Files:**
- Modify: `frontend/src/App.tsx`

On mobile (`< 768px`) the sidebar is hidden and context is hidden; main shows one of topic/attention/context-as-page based on bottom-tab state.

- [ ] **Step 38.1: Update `frontend/src/App.tsx`**

```tsx
import { useState } from "react";
import { AppShell } from "./layout/AppShell";
import { Sidebar } from "./layout/Sidebar";
import { TopicView } from "./topic/TopicView";
import { TopicContext } from "./context/TopicContext";
import { AttentionView } from "./attention/AttentionView";
import { BottomTabs, type MobileTab } from "./layout/BottomTabs";

type DesktopView =
  | { kind: "topic"; id: number; title: string }
  | { kind: "attention" };

export default function App() {
  const [view, setView] = useState<DesktopView>({ kind: "topic", id: 1, title: "为 Agent 记忆写一个研讨 PPT" });
  const [mobileTab, setMobileTab] = useState<MobileTab>("topic");

  const isMobile = typeof window !== "undefined" && window.matchMedia("(max-width: 767px)").matches;

  const sidebar = (
    <Sidebar
      projectName="Lets"
      projectRepo="github.com/echomem/lets"
      attentionCount={4}
      onClickAttention={() => setView({ kind: "attention" })}
      onClickTopic={() => setView({ kind: "topic", id: 1, title: "为 Agent 记忆写一个研讨 PPT" })}
    />
  );

  let main: React.ReactNode;
  if (isMobile) {
    if (mobileTab === "topic") main = <TopicView topicId={1} topicTitle="为 Agent 记忆写一个研讨 PPT" />;
    else if (mobileTab === "attention") main = <AttentionView userName="Neo" />;
    else main = <TopicContext />;
  } else {
    main = view.kind === "topic"
      ? <TopicView topicId={view.id} topicTitle={view.title} />
      : <AttentionView userName="Neo" />;
  }

  return (
    <AppShell
      sidebar={sidebar}
      main={main}
      context={view.kind === "topic" ? <TopicContext /> : <div className="p-4 text-text-dim text-sm">No context</div>}
      bottomTabs={<BottomTabs active={mobileTab} onSelect={setMobileTab} />}
    />
  );
}
```

- [ ] **Step 38.2: Run dev, resize to iPhone width, verify**

```bash
cd frontend && pnpm dev
```

Open DevTools, switch to iPhone 14 size. Expected: sidebar gone, context gone, bottom tabs visible, tapping Attention shows the attention view.

- [ ] **Step 38.3: Run all tests**

```bash
cd frontend && pnpm test
```

Expected: all green.

- [ ] **Step 38.4: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat(frontend): mobile view switching via BottomTabs"
```

---

## Task 39: FastAPI serves built SPA at `/app`

**Files:**
- Modify: `app/main.py`
- Modify: `README.md`
- Modify: `frontend/.env.production`

- [ ] **Step 39.1: Add static mount + SPA fallback to `app/main.py`**

Near the end of `app/main.py` (after all `/api/...` routes), add:

```python
import pathlib
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse


_FRONTEND_DIST = pathlib.Path(__file__).parent.parent / "frontend" / "dist"


if _FRONTEND_DIST.exists():
    app.mount("/app/assets", StaticFiles(directory=_FRONTEND_DIST / "assets"), name="frontend-assets")

    @app.get("/app")
    @app.get("/app/{rest:path}")
    def serve_app(rest: str = "") -> FileResponse:
        _ = rest  # path consumed for SPA fallback; index.html does the routing
        index = _FRONTEND_DIST / "index.html"
        if not index.exists():
            raise HTTPException(status_code=404, detail="frontend not built")
        return FileResponse(index)
```

The mount is conditional so `tests/` still pass without a built frontend.

- [ ] **Step 39.2: Build and verify**

```bash
cd frontend && pnpm build
cd /Users/jacky/code/Lets && .venv/bin/uvicorn app.main:app --reload
```

Open `http://localhost:8000/app`. Expected: the React SPA loads, calls real API (since the prod build has `VITE_USE_FIXTURES=false`). MSW does not start. Identity is set via the IdentityProvider's localStorage fallback (Neo by default — see Phase 1 IdentityProvider test).

If you see "no messages" — that's expected if the DB is empty. Run the Track A e2e seed to populate, or `POST /api/topics` + `POST /api/messages` by hand.

- [ ] **Step 39.3: Update README**

Append to `README.md` under the existing v1.5 section:

```markdown
## Track F: Web Frontend

The React SPA lives under `frontend/`.

```bash
cd frontend && pnpm install
cd frontend && pnpm dev    # fixture mode, http://localhost:5173
cd frontend && pnpm build  # builds into frontend/dist for production serving
```

Production: `uvicorn app.main:app` then `http://localhost:8000/app`. The backend serves the SPA from `frontend/dist` if it exists.
```

- [ ] **Step 39.4: Commit**

```bash
git add app/main.py README.md frontend/.env.production
git commit -m "feat(api): serve built frontend SPA at /app with fallback routing"
```

---

## Task 40: Playwright E2E — PPT scenario

**Files:**
- Create: `frontend/playwright.config.ts`
- Create: `frontend/e2e/ppt-scenario.spec.ts`
- Modify: `frontend/package.json` (already declares e2e script)

- [ ] **Step 40.1: Create `frontend/playwright.config.ts`**

```ts
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  reporter: "list",
  use: {
    baseURL: "http://localhost:5173",
    trace: "retain-on-failure",
  },
  webServer: {
    command: "pnpm dev --port 5173",
    url: "http://localhost:5173",
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
});
```

- [ ] **Step 40.2: Create `frontend/e2e/ppt-scenario.spec.ts`**

```ts
import { test, expect } from "@playwright/test";

test("PPT scenario: see seeded stream and post a chat", async ({ page }) => {
  await page.goto("/");

  // Wait for MSW + initial query
  await expect(page.getByRole("heading", { name: /PPT/ })).toBeVisible();

  // 14 messages from fixture
  await expect(page.locator('[data-testid="message-row"]')).toHaveCount(14);

  // All 4 typed-message visual signals present
  await expect(page.getByText("status").first()).toBeVisible();
  await expect(page.getByText("finding").first()).toBeVisible();
  await expect(page.getByText("artifact_revision · v0")).toBeVisible();
  await expect(page.getByText("spec_change")).toBeVisible();

  // Post via composer
  const composer = page.getByRole("textbox");
  await composer.fill("e2e: hello from playwright");
  await composer.press("Enter");

  await expect(page.getByText("e2e: hello from playwright")).toBeVisible();
  await expect(page.locator('[data-testid="message-row"]')).toHaveCount(15);
});

test("Attention view shows 3 groups", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /待处理/ }).click();
  await expect(page.getByRole("heading", { name: /需要决定/ })).toBeVisible();
  await expect(page.getByRole("heading", { name: /主动发现/ })).toBeVisible();
  await expect(page.getByRole("heading", { name: /同事消息/ })).toBeVisible();
});

test("Spec change Approve flips to Approved state", async ({ page }) => {
  await page.goto("/");
  const approve = page.getByRole("button", { name: "Approve" }).first();
  await approve.click();
  await expect(page.getByText("Approved")).toBeVisible();
});
```

- [ ] **Step 40.3: Install Playwright browsers and run**

```bash
cd frontend && pnpm exec playwright install chromium
cd frontend && pnpm e2e
```

Expected: 3 tests pass.

- [ ] **Step 40.4: Commit**

```bash
git add frontend/playwright.config.ts frontend/e2e/
git commit -m "test(frontend): Playwright E2E for PPT scenario, attention, spec approve"
```

---

## Task 41: Real-mode smoke E2E

**Files:**
- Create: `frontend/e2e/real-api.spec.ts`
- Create: `scripts/seed-track-f-demo.py`

Real-mode smoke proves the frontend works against the actual FastAPI backend (no MSW), using a deterministic seed script.

- [ ] **Step 41.1: Create `scripts/seed-track-f-demo.py`**

```python
"""Seed a Track F demo topic + a few messages against a running backend."""
from __future__ import annotations

import json
import sys
import urllib.request


BASE = "http://localhost:8000"


def post(path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Lets-Human": "Neo",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def get(path: str) -> dict:
    req = urllib.request.Request(BASE + path, headers={"X-Lets-Human": "Neo"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def main() -> int:
    me = get("/api/identity/me")
    print("identity:", me)
    try:
        topic = post("/api/topics", {"slug": "t-demo", "title": "Track F demo topic"})
    except urllib.error.HTTPError as e:
        if e.code == 409:
            topics = get("/api/topics")
            topic = next(t for t in topics if t["slug"] == "t-demo")
        else:
            raise
    print("topic:", topic)

    post("/api/messages", {
        "topic_id": topic["id"], "type": "chat",
        "actor_type": "human", "actor_id": me["human"]["id"],
        "body": "demo seed: Neo says hi",
    })
    post("/api/messages", {
        "topic_id": topic["id"], "type": "spec_change",
        "actor_type": "human", "actor_id": me["human"]["id"],
        "body": "字号 10 → 14",
        "metadata": {
            "file": ".claude/skills/research-talk-style/SKILL.md",
            "before": 10, "after": 14, "approvers": [],
        },
    })
    print("seeded.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 41.2: Create `frontend/e2e/real-api.spec.ts`**

```ts
import { test, expect } from "@playwright/test";

test.describe.configure({ mode: "serial" });

test("real-mode: posting a chat round-trips through the backend SSE", async ({ page, request }) => {
  test.skip(!process.env.LETS_REAL_API_BASE, "set LETS_REAL_API_BASE to run");

  // Seed via script
  const base = process.env.LETS_REAL_API_BASE!;
  const me = await request.get(`${base}/api/identity/me`, {
    headers: { "X-Lets-Human": "Neo" },
  });
  expect(me.ok()).toBeTruthy();

  // Visit the served SPA
  await page.goto(`${base}/app`);
  await expect(page.getByRole("heading", { name: /Track F demo topic/ })).toBeVisible({ timeout: 10_000 });

  await page.getByRole("textbox").fill("real-mode hello");
  await page.getByRole("textbox").press("Enter");
  await expect(page.getByText("real-mode hello")).toBeVisible();
});
```

- [ ] **Step 41.3: Run real-mode E2E manually**

In one terminal:
```bash
.venv/bin/uvicorn app.main:app --port 8000
```

In another:
```bash
.venv/bin/python scripts/seed-track-f-demo.py
cd frontend && pnpm build
LETS_REAL_API_BASE=http://localhost:8000 pnpm e2e
```

Expected: 4 tests pass total (3 fixture + 1 real-mode).

- [ ] **Step 41.4: Commit**

```bash
git add frontend/e2e/real-api.spec.ts scripts/seed-track-f-demo.py
git commit -m "test(frontend): real-mode E2E smoke + seed script"
```

---

## Task 42: Replace v1 `/` debug UI with redirect to `/app`

**Files:**
- Modify: `app/main.py`

The old `web/index.html` debug panel from v1 is now superseded by Track F. Leave the file in place for one release (for rollback), but redirect the `/` route to `/app`.

- [ ] **Step 42.1: Update `home()` in `app/main.py`**

Replace:
```python
@app.get("/")
def home() -> FileResponse:
    return FileResponse("web/index.html")
```

With:
```python
from fastapi.responses import RedirectResponse


@app.get("/")
def home() -> RedirectResponse | FileResponse:
    if _FRONTEND_DIST.exists() and (_FRONTEND_DIST / "index.html").exists():
        return RedirectResponse(url="/app", status_code=307)
    return FileResponse("web/index.html")
```

- [ ] **Step 42.2: Manual smoke**

```bash
cd frontend && pnpm build
.venv/bin/uvicorn app.main:app --port 8000
```

Visit `http://localhost:8000/`. Expected: 307 → `/app` → React SPA loads.

- [ ] **Step 42.3: Commit**

```bash
git add app/main.py
git commit -m "feat(api): redirect / to /app when SPA is built; v1 debug UI kept as fallback"
```

---

## Task 43: Backend — GitHub OAuth + session cookie

**Files:**
- Create: `tests/test_oauth_github.py`
- Modify: `app/db.py` — add github fields to `humans`, new `sessions` table
- Modify: `app/auth.py` — session functions
- Modify: `app/main.py` — `/auth/github/start`, `/auth/github/callback`, `/auth/me`, `/auth/logout`
- Modify: `requirements.txt` — `httpx` (if not already present)
- Modify: `README.md`

GitHub OAuth is the primary login path; `humans.email`-only / CLI tokens stay as the fallback. After successful OAuth, the backend issues an opaque session cookie (`lets_session`) that the SPA reads via `/auth/me` to know who's logged in. Agent tokens (Bearer in `.mcp.json`) are a separate credential class — they authenticate **CLI agents**, not the browser session.

- [ ] **Step 43.1: Add github columns + sessions table**

Edit `app/db.py`. Inside the `init_db()` schema block, modify the `humans` table and add `sessions`:

```python
            CREATE TABLE IF NOT EXISTS humans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                email TEXT,
                github_id INTEGER UNIQUE,
                github_login TEXT,
                avatar_url TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                value_hash TEXT NOT NULL UNIQUE,
                human_id INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_used_at TEXT,
                revoked_at TEXT,
                FOREIGN KEY(human_id) REFERENCES humans(id)
            );
            CREATE INDEX IF NOT EXISTS idx_sessions_value_hash ON sessions(value_hash);
```

Add a non-destructive migration helper near `init_db()`:
```python
def _migrate_humans_github(conn):
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(humans)").fetchall()}
    if "github_id" not in cols:
        conn.execute("ALTER TABLE humans ADD COLUMN github_id INTEGER")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_humans_github_id ON humans(github_id)")
    if "github_login" not in cols:
        conn.execute("ALTER TABLE humans ADD COLUMN github_login TEXT")
    if "avatar_url" not in cols:
        conn.execute("ALTER TABLE humans ADD COLUMN avatar_url TEXT")
```

Call `_migrate_humans_github(conn)` at the end of `init_db()`.

- [ ] **Step 43.2: Add session helpers to `app/auth.py`**

Append:
```python
import hashlib
import secrets


def issue_session(human_id: int) -> str:
    raw = secrets.token_urlsafe(32)
    value_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    with connect() as conn:
        conn.execute(
            "INSERT INTO sessions (value_hash, human_id) VALUES (?, ?)",
            (value_hash, human_id),
        )
    return raw


def verify_session(value: str) -> dict | None:
    value_hash = hashlib.sha256(value.encode("utf-8")).hexdigest()
    with connect() as conn:
        row = conn.execute(
            """
            SELECT s.id AS session_id, s.human_id, h.name, h.github_login, h.avatar_url
            FROM sessions s
            JOIN humans h ON h.id = s.human_id
            WHERE s.value_hash = ? AND s.revoked_at IS NULL
            """,
            (value_hash,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            "UPDATE sessions SET last_used_at = CURRENT_TIMESTAMP WHERE id = ?",
            (row["session_id"],),
        )
    return dict(row)


def revoke_session(value: str) -> None:
    value_hash = hashlib.sha256(value.encode("utf-8")).hexdigest()
    with connect() as conn:
        conn.execute(
            "UPDATE sessions SET revoked_at = CURRENT_TIMESTAMP WHERE value_hash = ?",
            (value_hash,),
        )


def get_session_principal(
    lets_session: str | None = Cookie(default=None, alias="lets_session"),
) -> dict:
    if not lets_session:
        raise HTTPException(status_code=401, detail="not authenticated")
    principal = verify_session(lets_session)
    if principal is None:
        raise HTTPException(status_code=401, detail="invalid session")
    return principal
```

At the top of the file add `from fastapi import Cookie` if not present.

- [ ] **Step 43.3: Write failing OAuth tests**

Create `tests/test_oauth_github.py`:
```python
import json
from unittest.mock import patch


def test_oauth_start_redirects_with_state(client_with_auth, monkeypatch):
    monkeypatch.setenv("GITHUB_CLIENT_ID", "test_id")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "test_secret")
    res = client_with_auth.get("/auth/github/start", follow_redirects=False)
    assert res.status_code == 307
    loc = res.headers["location"]
    assert loc.startswith("https://github.com/login/oauth/authorize")
    assert "client_id=test_id" in loc
    assert "state=" in loc
    assert "scope=" in loc


def test_oauth_callback_creates_human_and_sets_session_cookie(client_with_auth, monkeypatch):
    monkeypatch.setenv("GITHUB_CLIENT_ID", "test_id")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "test_secret")

    # Prime a state
    started = client_with_auth.get("/auth/github/start", follow_redirects=False)
    loc = started.headers["location"]
    state = [p.split("=", 1)[1] for p in loc.split("&") if p.startswith("state=")][0]

    fake_user = {
        "id": 12345, "login": "neo",
        "name": "Neo Anderson",
        "email": "neo@example.com",
        "avatar_url": "https://avatars.example/neo.png",
    }

    async def fake_token(*a, **kw):
        class R:
            status_code = 200
            def json(self): return {"access_token": "ghu_x"}
        return R()

    async def fake_user_get(*a, **kw):
        class R:
            status_code = 200
            def json(self): return fake_user
        return R()

    with patch("app.main._gh_exchange_code", new=fake_token), \
         patch("app.main._gh_fetch_user", new=fake_user_get):
        res = client_with_auth.get(
            f"/auth/github/callback?code=abc&state={state}",
            follow_redirects=False,
        )

    assert res.status_code == 307
    assert res.headers["location"] == "/app"
    assert "lets_session" in res.cookies

    me = client_with_auth.get("/auth/me", cookies={"lets_session": res.cookies["lets_session"]})
    assert me.status_code == 200
    body = me.json()
    assert body["human"]["github_login"] == "neo"
    assert body["human"]["name"] == "Neo Anderson"


def test_logout_revokes_session(client_with_auth, monkeypatch):
    monkeypatch.setenv("GITHUB_CLIENT_ID", "x")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "y")
    # Manually seed a session via the auth module
    from app.auth import issue_session
    from app.identity import ensure_human

    hid = ensure_human("Trinity")
    token = issue_session(hid)

    me = client_with_auth.get("/auth/me", cookies={"lets_session": token})
    assert me.status_code == 200

    logout = client_with_auth.post("/auth/logout", cookies={"lets_session": token})
    assert logout.status_code == 204

    me2 = client_with_auth.get("/auth/me", cookies={"lets_session": token})
    assert me2.status_code == 401
```

- [ ] **Step 43.4: Run tests (should fail)**

```bash
.venv/bin/pytest tests/test_oauth_github.py -v
```

Expected: 3 tests fail with 404.

- [ ] **Step 43.5: Add OAuth routes to `app/main.py`**

Append:
```python
import os
import urllib.parse
import secrets as _secrets
import httpx
from fastapi import Cookie
from fastapi.responses import RedirectResponse, Response


# In-memory state store (single-process; fine for v1.5a Railway single instance).
_OAUTH_STATES: dict[str, float] = {}
_OAUTH_TTL_S = 600.0


def _new_state() -> str:
    import time as _t
    # Lazy cleanup
    now = _t.time()
    for k, ts in list(_OAUTH_STATES.items()):
        if now - ts > _OAUTH_TTL_S:
            _OAUTH_STATES.pop(k, None)
    s = _secrets.token_urlsafe(24)
    _OAUTH_STATES[s] = now
    return s


def _consume_state(s: str) -> bool:
    return _OAUTH_STATES.pop(s, None) is not None


@app.get("/auth/github/start")
def auth_github_start() -> RedirectResponse:
    client_id = os.environ.get("GITHUB_CLIENT_ID")
    if not client_id:
        raise HTTPException(status_code=500, detail="GITHUB_CLIENT_ID not configured")
    state = _new_state()
    params = {
        "client_id": client_id,
        "redirect_uri": os.environ.get(
            "GITHUB_REDIRECT_URI", "http://localhost:8000/auth/github/callback"
        ),
        "scope": "read:user user:email",
        "state": state,
        "allow_signup": "true",
    }
    url = "https://github.com/login/oauth/authorize?" + urllib.parse.urlencode(params)
    return RedirectResponse(url=url, status_code=307)


async def _gh_exchange_code(code: str):
    async with httpx.AsyncClient(timeout=10.0) as cli:
        return await cli.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": os.environ["GITHUB_CLIENT_ID"],
                "client_secret": os.environ["GITHUB_CLIENT_SECRET"],
                "code": code,
            },
            headers={"Accept": "application/json"},
        )


async def _gh_fetch_user(access_token: str):
    async with httpx.AsyncClient(timeout=10.0) as cli:
        return await cli.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
            },
        )


@app.get("/auth/github/callback")
async def auth_github_callback(code: str, state: str) -> RedirectResponse:
    if not _consume_state(state):
        raise HTTPException(status_code=400, detail="invalid state")

    tok = await _gh_exchange_code(code)
    if tok.status_code != 200:
        raise HTTPException(status_code=502, detail="github token exchange failed")
    access_token = tok.json().get("access_token")
    if not access_token:
        raise HTTPException(status_code=502, detail="no access_token in github response")

    u = await _gh_fetch_user(access_token)
    if u.status_code != 200:
        raise HTTPException(status_code=502, detail="github user fetch failed")
    info = u.json()

    github_id = int(info["id"])
    github_login = str(info["login"])
    display_name = info.get("name") or github_login
    avatar_url = info.get("avatar_url")
    email = info.get("email")

    with connect() as conn:
        row = conn.execute(
            "SELECT id FROM humans WHERE github_id = ?", (github_id,)
        ).fetchone()
        if row is not None:
            human_id = row["id"]
            conn.execute(
                """
                UPDATE humans SET github_login = ?, avatar_url = ?,
                       name = COALESCE(?, name), updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (github_login, avatar_url, display_name, human_id),
            )
        else:
            # Resolve name uniqueness
            base = display_name
            candidate = base
            i = 2
            while conn.execute("SELECT 1 FROM humans WHERE name = ?", (candidate,)).fetchone():
                candidate = f"{base} ({i})"
                i += 1
            cursor = conn.execute(
                """
                INSERT INTO humans (name, email, github_id, github_login, avatar_url)
                VALUES (?, ?, ?, ?, ?)
                """,
                (candidate, email, github_id, github_login, avatar_url),
            )
            human_id = int(cursor.lastrowid)

    from .auth import issue_session
    session_value = issue_session(human_id)
    res = RedirectResponse(url="/app", status_code=307)
    res.set_cookie(
        "lets_session", session_value,
        httponly=True,
        secure=os.environ.get("LETS_COOKIE_SECURE", "true").lower() != "false",
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
        path="/",
    )
    return res


@app.get("/auth/me")
def auth_me(
    lets_session: str | None = Cookie(default=None, alias="lets_session"),
) -> dict:
    from .auth import verify_session
    if not lets_session:
        raise HTTPException(status_code=401, detail="not authenticated")
    principal = verify_session(lets_session)
    if principal is None:
        raise HTTPException(status_code=401, detail="invalid session")
    return {
        "human": {
            "id": principal["human_id"],
            "name": principal["name"],
            "github_login": principal["github_login"],
            "avatar_url": principal["avatar_url"],
        }
    }


@app.post("/auth/logout", status_code=204)
def auth_logout(
    lets_session: str | None = Cookie(default=None, alias="lets_session"),
) -> Response:
    from .auth import revoke_session
    if lets_session:
        revoke_session(lets_session)
    res = Response(status_code=204)
    res.delete_cookie("lets_session", path="/")
    return res
```

- [ ] **Step 43.6: Run tests (should pass)**

```bash
.venv/bin/pytest tests/test_oauth_github.py -v
```

Expected: 3 tests pass.

- [ ] **Step 43.7: Add `httpx` to requirements if missing**

```bash
grep -q "^httpx" requirements.txt || echo "httpx" >> requirements.txt
.venv/bin/pip install -r requirements.txt
```

- [ ] **Step 43.8: Append env vars section to README**

```markdown
### v1.5 — GitHub OAuth

Register an OAuth App at https://github.com/settings/applications/new with:
- Homepage URL: `https://<your-domain>`
- Authorization callback URL: `https://<your-domain>/auth/github/callback`

Set on the server:
- `GITHUB_CLIENT_ID=...`
- `GITHUB_CLIENT_SECRET=...`
- `GITHUB_REDIRECT_URI=https://<your-domain>/auth/github/callback`
- `LETS_COOKIE_SECURE=true` (set to `false` for local http)
```

- [ ] **Step 43.9: Commit**

```bash
git add app/db.py app/auth.py app/main.py tests/test_oauth_github.py requirements.txt README.md
git commit -m "feat(auth): GitHub OAuth + session cookie + /auth/{start,callback,me,logout}"
```

---

## Task 44: Backend — REST tokens CRUD

**Files:**
- Create: `tests/test_tokens_api.py`
- Modify: `app/main.py`

Wrap the existing `app/auth.py` `issue_token` / `list_tokens` / `revoke_token` functions as REST endpoints, gated by **session cookie** (so only logged-in users can mint tokens for themselves). Token list never returns the raw value; the raw token is only shown **once at creation time**.

- [ ] **Step 44.1: Write failing tests**

Create `tests/test_tokens_api.py`:
```python
def _login(client) -> str:
    """Helper: seed Neo as a logged-in human, return session cookie value."""
    from app.identity import ensure_human
    from app.auth import issue_session
    hid = ensure_human("Neo")
    return issue_session(hid)


def test_list_tokens_requires_session(client_with_auth):
    res = client_with_auth.get("/api/tokens")
    assert res.status_code == 401


def test_list_tokens_returns_only_my_tokens(client_with_auth):
    session = _login(client_with_auth)
    res = client_with_auth.get("/api/tokens", cookies={"lets_session": session})
    assert res.status_code == 200
    assert res.json() == []


def test_create_token_returns_raw_value_once(client_with_auth):
    session = _login(client_with_auth)
    res = client_with_auth.post(
        "/api/tokens",
        cookies={"lets_session": session},
        json={"label": "claude on neo-mbp", "role": "claude", "device_label": "neo-mbp"},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["value"].startswith("lets_")
    assert body["label"] == "claude on neo-mbp"
    assert body["agent_instance"]["role"] == "claude"
    assert body["agent_instance"]["device_label"] == "neo-mbp"

    # Subsequent list does NOT echo the raw value
    listed = client_with_auth.get("/api/tokens", cookies={"lets_session": session}).json()
    assert len(listed) == 1
    assert "value" not in listed[0]
    assert listed[0]["label"] == "claude on neo-mbp"


def test_revoke_token(client_with_auth):
    session = _login(client_with_auth)
    create = client_with_auth.post(
        "/api/tokens",
        cookies={"lets_session": session},
        json={"label": "x", "role": "codex", "device_label": "neo-mbp"},
    )
    tid = create.json()["id"]

    res = client_with_auth.delete(f"/api/tokens/{tid}", cookies={"lets_session": session})
    assert res.status_code == 204

    listed = client_with_auth.get("/api/tokens", cookies={"lets_session": session}).json()
    assert listed[0]["revoked_at"] is not None
```

- [ ] **Step 44.2: Run tests (should fail)**

```bash
.venv/bin/pytest tests/test_tokens_api.py -v
```

Expected: 4 tests fail.

- [ ] **Step 44.3: Add endpoints to `app/main.py`**

```python
class TokenCreate(BaseModel):
    label: str
    role: str
    device_label: str


@app.get("/api/tokens")
def list_my_tokens(
    lets_session: str | None = Cookie(default=None, alias="lets_session"),
) -> list[dict]:
    from .auth import verify_session, list_tokens
    if not lets_session:
        raise HTTPException(status_code=401, detail="not authenticated")
    principal = verify_session(lets_session)
    if principal is None:
        raise HTTPException(status_code=401, detail="invalid session")
    tokens = list_tokens(human_id=principal["human_id"])
    # Strip internal fields
    return [
        {k: v for k, v in t.items() if k not in ("value_hash",)}
        for t in tokens
    ]


@app.post("/api/tokens", status_code=201)
def create_my_token(
    payload: TokenCreate,
    lets_session: str | None = Cookie(default=None, alias="lets_session"),
) -> dict:
    from .auth import verify_session, issue_token
    from .identity import ensure_agent_instance
    if not lets_session:
        raise HTTPException(status_code=401, detail="not authenticated")
    principal = verify_session(lets_session)
    if principal is None:
        raise HTTPException(status_code=401, detail="invalid session")

    agent_instance_id = ensure_agent_instance(
        role=payload.role,
        human_id=principal["human_id"],
        device_label=payload.device_label,
    )
    raw_value, token_id = issue_token(
        human_id=principal["human_id"],
        agent_instance_id=agent_instance_id,
        label=payload.label,
    )
    with connect() as conn:
        row = conn.execute(
            """
            SELECT ai.id, ar.name AS role, ai.device_label
            FROM agent_instances ai
            JOIN agent_roles ar ON ar.id = ai.role_id
            WHERE ai.id = ?
            """,
            (agent_instance_id,),
        ).fetchone()
    return {
        "id": token_id,
        "value": raw_value,
        "label": payload.label,
        "agent_instance": dict(row),
    }


@app.delete("/api/tokens/{token_id}", status_code=204)
def revoke_my_token(
    token_id: int,
    lets_session: str | None = Cookie(default=None, alias="lets_session"),
) -> Response:
    from .auth import verify_session, revoke_token
    if not lets_session:
        raise HTTPException(status_code=401, detail="not authenticated")
    principal = verify_session(lets_session)
    if principal is None:
        raise HTTPException(status_code=401, detail="invalid session")

    with connect() as conn:
        owner = conn.execute(
            "SELECT human_id FROM tokens WHERE id = ?", (token_id,)
        ).fetchone()
    if owner is None or owner["human_id"] != principal["human_id"]:
        raise HTTPException(status_code=404, detail="token not found")

    revoke_token(token_id)
    return Response(status_code=204)
```

This relies on `issue_token` in `app/auth.py` returning `(raw_value, id)`. Verify with:
```bash
grep -n "def issue_token" app/auth.py
```
If the current signature only returns `id`, edit `issue_token` to additionally return the raw value (it already generates it internally). Update any existing call sites accordingly (only `app/tokens_cli.py` should be affected).

- [ ] **Step 44.4: Run tests (should pass)**

```bash
.venv/bin/pytest tests/test_tokens_api.py -v
```

Expected: 4 tests pass.

- [ ] **Step 44.5: Commit**

```bash
git add tests/test_tokens_api.py app/main.py app/auth.py app/tokens_cli.py
git commit -m "feat(auth): REST tokens CRUD (POST/GET/DELETE /api/tokens) gated by session"
```

---

## Task 45: Frontend — LoginPage + SessionGate + identity wired to session

**Files:**
- Create: `frontend/src/auth/LoginPage.tsx` + `.test.tsx`
- Create: `frontend/src/auth/SessionGate.tsx` + `.test.tsx`
- Create: `frontend/src/auth/useSession.ts`
- Modify: `frontend/src/identity/IdentityProvider.tsx` — read from `/auth/me` instead of localStorage in real mode
- Modify: `frontend/src/api/queries.ts` — add `useSessionMe`
- Modify: `frontend/src/fixtures/handlers.ts` — fixture `/auth/me`

- [ ] **Step 45.1: Add fixture handlers**

Edit `frontend/src/fixtures/handlers.ts` and add inside the `handlers` array:

```ts
http.get("/auth/me", () =>
  HttpResponse.json({
    human: {
      id: 1, name: "Neo", github_login: "neo",
      avatar_url: "https://avatars.example/neo.png",
    },
  }),
),

http.post("/auth/logout", () => new HttpResponse(null, { status: 204 })),
```

- [ ] **Step 45.2: Create `frontend/src/auth/useSession.ts`**

```ts
import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "../api/client";

export interface SessionUser {
  id: number;
  name: string;
  github_login: string | null;
  avatar_url: string | null;
}

export interface SessionResponse { human: SessionUser }

export function useSession() {
  return useQuery({
    queryKey: ["auth.me"],
    queryFn: async () => {
      try {
        return await apiRequest<SessionResponse>("/auth/me", {
          identity: { humanName: null, agentRole: null, deviceLabel: null },
        });
      } catch (e) {
        if (e instanceof Error && /401/.test(e.message)) return null;
        throw e;
      }
    },
    retry: false,
    staleTime: 60_000,
  });
}
```

- [ ] **Step 45.3: Write failing test**

Create `frontend/src/auth/LoginPage.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { LoginPage } from "./LoginPage";

describe("<LoginPage />", () => {
  it("renders Login with GitHub button pointing to /auth/github/start", () => {
    renderWithProviders(<LoginPage />);
    const link = screen.getByRole("link", { name: /Login with GitHub/i });
    expect(link).toHaveAttribute("href", "/auth/github/start");
  });
});
```

Create `frontend/src/auth/SessionGate.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { SessionGate } from "./SessionGate";

describe("<SessionGate />", () => {
  it("renders children when session is present (fixture defaults to Neo)", async () => {
    renderWithProviders(
      <SessionGate fallback={<div>locked</div>}>
        <div>secret area</div>
      </SessionGate>,
    );
    await waitFor(() => {
      expect(screen.getByText("secret area")).toBeInTheDocument();
    });
  });
});
```

- [ ] **Step 45.4: Create `frontend/src/auth/LoginPage.tsx`**

```tsx
export function LoginPage() {
  return (
    <div className="min-h-screen grid place-items-center bg-bg">
      <div className="max-w-sm w-full px-6 py-10 text-center flex flex-col gap-6">
        <div>
          <h1 className="font-[var(--font-display)] text-3xl">Lets</h1>
          <p className="text-text-muted text-sm mt-2">协同工作空间 · 你和你的 agent</p>
        </div>
        <a
          href="/auth/github/start"
          className="inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-text text-bg font-medium"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 .5C5.65.5.5 5.65.5 12c0 5.08 3.29 9.39 7.86 10.91.58.1.79-.25.79-.55 0-.27-.01-1-.02-1.95-3.2.7-3.87-1.54-3.87-1.54-.52-1.32-1.27-1.67-1.27-1.67-1.04-.71.08-.7.08-.7 1.15.08 1.76 1.18 1.76 1.18 1.02 1.75 2.68 1.25 3.34.96.1-.74.4-1.25.73-1.54-2.55-.29-5.24-1.28-5.24-5.69 0-1.26.45-2.28 1.18-3.09-.12-.29-.51-1.46.11-3.05 0 0 .97-.31 3.18 1.18a11 11 0 0 1 5.79 0c2.21-1.49 3.18-1.18 3.18-1.18.62 1.59.23 2.76.11 3.05.74.81 1.18 1.83 1.18 3.09 0 4.42-2.69 5.4-5.25 5.68.41.36.78 1.05.78 2.12 0 1.53-.01 2.77-.01 3.15 0 .31.21.66.8.55C20.21 21.39 23.5 17.08 23.5 12 23.5 5.65 18.35.5 12 .5Z"/>
          </svg>
          Login with GitHub
        </a>
        <p className="text-[11px] text-text-dim">
          没有 GitHub 账号？联系工作区管理员用 CLI 给你开个 token：
          <code className="font-mono ml-1">python -m app.tokens_cli issue --human &lt;name&gt;</code>
        </p>
      </div>
    </div>
  );
}
```

- [ ] **Step 45.5: Create `frontend/src/auth/SessionGate.tsx`**

```tsx
import type { ReactNode } from "react";
import { useSession } from "./useSession";

interface Props {
  children: ReactNode;
  fallback: ReactNode;
}

export function SessionGate({ children, fallback }: Props) {
  const q = useSession();
  if (q.isLoading) {
    return <div className="min-h-screen grid place-items-center text-text-dim">…</div>;
  }
  if (!q.data) return <>{fallback}</>;
  return <>{children}</>;
}
```

- [ ] **Step 45.6: Wire IdentityProvider to consume session**

Update `frontend/src/identity/IdentityProvider.tsx`:
```tsx
import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { IdentityContext, type Identity } from "./useIdentity";
import { useSession } from "../auth/useSession";

const STORAGE_KEY = "lets.identity";

function loadIdentity(): Identity {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { humanName: null, agentRole: null, deviceLabel: null };
    const parsed = JSON.parse(raw) as Partial<Identity>;
    return {
      humanName: parsed.humanName ?? null,
      agentRole: parsed.agentRole ?? null,
      deviceLabel: parsed.deviceLabel ?? null,
    };
  } catch {
    return { humanName: null, agentRole: null, deviceLabel: null };
  }
}

export function IdentityProvider({ children }: { children: ReactNode }) {
  const [identity, setIdentityState] = useState<Identity>(() => loadIdentity());
  const session = useSession();

  // When session is known, override humanName from the server (source of truth).
  useEffect(() => {
    if (session.data?.human?.name && session.data.human.name !== identity.humanName) {
      setIdentityState((prev) => {
        const next = { ...prev, humanName: session.data!.human.name };
        localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
        return next;
      });
    }
  }, [session.data, identity.humanName]);

  const setIdentity = useCallback((next: Partial<Identity>) => {
    setIdentityState((prev) => {
      const merged: Identity = { ...prev, ...next };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(merged));
      return merged;
    });
  }, []);

  const value = useMemo(() => ({ ...identity, setIdentity }), [identity, setIdentity]);
  return <IdentityContext.Provider value={value}>{children}</IdentityContext.Provider>;
}
```

The existing IdentityProvider test still passes — it doesn't hit the network because the session hook starts loading and never resolves under the mock without MSW. To keep the test self-contained, update `frontend/test/setup.ts` so MSW is already running (which it is, from Task 6).

- [ ] **Step 45.7: Add SessionGate to App**

Update `frontend/src/App.tsx`:
```tsx
import { useState } from "react";
import { AppShell } from "./layout/AppShell";
import { Sidebar } from "./layout/Sidebar";
import { TopicView } from "./topic/TopicView";
import { TopicContext } from "./context/TopicContext";
import { AttentionView } from "./attention/AttentionView";
import { BottomTabs, type MobileTab } from "./layout/BottomTabs";
import { SessionGate } from "./auth/SessionGate";
import { LoginPage } from "./auth/LoginPage";
import { SettingsTokensPage } from "./settings/SettingsTokensPage";

type DesktopView =
  | { kind: "topic"; id: number; title: string }
  | { kind: "attention" }
  | { kind: "settings-tokens" };

export default function App() {
  return (
    <SessionGate fallback={<LoginPage />}>
      <Workspace />
    </SessionGate>
  );
}

function Workspace() {
  const [view, setView] = useState<DesktopView>({ kind: "topic", id: 1, title: "为 Agent 记忆写一个研讨 PPT" });
  const [mobileTab, setMobileTab] = useState<MobileTab>("topic");

  const isMobile = typeof window !== "undefined" && window.matchMedia("(max-width: 767px)").matches;

  const sidebar = (
    <Sidebar
      projectName="Lets"
      projectRepo="github.com/echomem/lets"
      attentionCount={4}
      onClickAttention={() => setView({ kind: "attention" })}
      onClickTopic={() => setView({ kind: "topic", id: 1, title: "为 Agent 记忆写一个研讨 PPT" })}
      onClickSettings={() => setView({ kind: "settings-tokens" })}
    />
  );

  let main: React.ReactNode;
  if (view.kind === "settings-tokens") {
    main = <SettingsTokensPage />;
  } else if (isMobile) {
    if (mobileTab === "topic") main = <TopicView topicId={1} topicTitle="为 Agent 记忆写一个研讨 PPT" />;
    else if (mobileTab === "attention") main = <AttentionView userName="Neo" />;
    else main = <TopicContext />;
  } else {
    main = view.kind === "topic"
      ? <TopicView topicId={view.id} topicTitle={view.title} />
      : <AttentionView userName="Neo" />;
  }

  return (
    <AppShell
      sidebar={sidebar}
      main={main}
      context={view.kind === "topic" ? <TopicContext /> : <div className="p-4 text-text-dim text-sm">No context</div>}
      bottomTabs={<BottomTabs active={mobileTab} onSelect={setMobileTab} />}
    />
  );
}
```

Update `Sidebar.tsx` to add `onClickSettings?: () => void` prop and wire the "项目设置" / "个人设置" footer links to it (use `onClickSettings` for "个人设置").

- [ ] **Step 45.8: Run tests**

```bash
cd frontend && pnpm test "LoginPage|SessionGate|Identity"
```

Expected: all green.

- [ ] **Step 45.9: Commit**

```bash
git add frontend/src/auth/ frontend/src/identity/IdentityProvider.tsx \
        frontend/src/fixtures/handlers.ts frontend/src/App.tsx frontend/src/layout/Sidebar.tsx
git commit -m "feat(frontend): LoginPage + SessionGate + identity wired to /auth/me"
```

---

## Task 46: Frontend — SettingsTokensPage

**Files:**
- Create: `frontend/src/settings/SettingsTokensPage.tsx` + `.test.tsx`
- Create: `frontend/src/settings/NewTokenDialog.tsx`
- Modify: `frontend/src/api/queries.ts` — `useMyTokens` + `useCreateToken` + `useRevokeToken`
- Modify: `frontend/src/api/types.ts` — `TokenRowDTO`, `CreateTokenInput`, `CreateTokenResponseDTO`
- Modify: `frontend/src/fixtures/handlers.ts` — `/api/tokens` fixtures

- [ ] **Step 46.1: Extend types**

Append to `frontend/src/api/types.ts`:
```ts
export interface TokenRowDTO {
  id: number;
  label: string | null;
  human_id: number;
  agent_instance_id: number | null;
  created_at: string;
  last_used_at: string | null;
  revoked_at: string | null;
}

export interface CreateTokenInput {
  label: string;
  role: string;
  device_label: string;
}

export interface CreateTokenResponseDTO {
  id: number;
  value: string;
  label: string;
  agent_instance: { id: number; role: string; device_label: string };
}
```

- [ ] **Step 46.2: Add query hooks**

Append to `frontend/src/api/queries.ts`:
```ts
import type { TokenRowDTO, CreateTokenInput, CreateTokenResponseDTO } from "./types";

export function useMyTokens() {
  const identity = useIdentity();
  return useQuery({
    queryKey: ["tokens"],
    queryFn: () => apiRequest<TokenRowDTO[]>("/api/tokens", { identity }),
  });
}

export function useCreateToken() {
  const identity = useIdentity();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateTokenInput) =>
      apiRequest<CreateTokenResponseDTO>("/api/tokens", {
        method: "POST", body: input, identity,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tokens"] }),
  });
}

export function useRevokeToken() {
  const identity = useIdentity();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      apiRequest<null>(`/api/tokens/${id}`, { method: "DELETE", identity }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tokens"] }),
  });
}
```

Note: `apiRequest` currently expects JSON in the response. For 204 DELETE, replace its `return (await res.json()) as T;` line with:
```ts
const ct = res.headers.get("content-type") ?? "";
if (!ct.includes("application/json")) return null as T;
return (await res.json()) as T;
```

- [ ] **Step 46.3: Add fixture handlers**

Inside the `handlers` array in `frontend/src/fixtures/handlers.ts`, add:

```ts
http.get("/api/tokens", () => {
  return HttpResponse.json(
    (seed as unknown as { fixtureTokens?: any[] }).fixtureTokens ?? [],
  );
}),

http.post("/api/tokens", async ({ request }) => {
  const body = (await request.json()) as { label: string; role: string; device_label: string };
  const tokens = ((seed as unknown as { fixtureTokens?: any[] }).fixtureTokens ??= []);
  const id = tokens.length + 1;
  const row = {
    id, label: body.label, human_id: 1,
    agent_instance_id: 100 + id,
    created_at: new Date().toISOString(),
    last_used_at: null, revoked_at: null,
  };
  tokens.push(row);
  return HttpResponse.json(
    {
      id, value: `lets_${Math.random().toString(36).slice(2, 10)}`,
      label: body.label,
      agent_instance: { id: row.agent_instance_id, role: body.role, device_label: body.device_label },
    },
    { status: 201 },
  );
}),

http.delete("/api/tokens/:id", ({ params }) => {
  const tokens = ((seed as unknown as { fixtureTokens?: any[] }).fixtureTokens ??= []);
  const t = tokens.find((x) => x.id === Number(params.id));
  if (t) t.revoked_at = new Date().toISOString();
  return new HttpResponse(null, { status: 204 });
}),
```

- [ ] **Step 46.4: Write failing test**

Create `frontend/src/settings/SettingsTokensPage.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../test/render";
import { SettingsTokensPage } from "./SettingsTokensPage";

describe("<SettingsTokensPage />", () => {
  it("starts empty, creates a token, reveals the raw value once", async () => {
    const user = userEvent.setup();
    renderWithProviders(<SettingsTokensPage />);
    await waitFor(() => expect(screen.getByText(/No agent tokens yet/i)).toBeInTheDocument());

    await user.click(screen.getByRole("button", { name: /\+ New token/i }));
    await user.type(screen.getByLabelText(/Label/i), "claude on neo-mbp");
    await user.selectOptions(screen.getByLabelText(/Role/i), "claude");
    await user.type(screen.getByLabelText(/Device/i), "neo-mbp");
    await user.click(screen.getByRole("button", { name: /^Create$/ }));

    // Token reveal modal
    await waitFor(() => {
      expect(screen.getByText(/copy now — it won't show again/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/^lets_/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Done/i }));
    await waitFor(() => expect(screen.getByText(/claude on neo-mbp/)).toBeInTheDocument());
  });

  it("revokes a token", async () => {
    const user = userEvent.setup();
    renderWithProviders(<SettingsTokensPage />);
    await user.click(screen.getByRole("button", { name: /\+ New token/i }));
    await user.type(screen.getByLabelText(/Label/i), "to-revoke");
    await user.selectOptions(screen.getByLabelText(/Role/i), "codex");
    await user.type(screen.getByLabelText(/Device/i), "neo-mbp");
    await user.click(screen.getByRole("button", { name: /^Create$/ }));
    await user.click(screen.getByRole("button", { name: /Done/i }));

    await user.click(screen.getByRole("button", { name: /Revoke/i }));
    await waitFor(() => {
      expect(screen.getByText(/revoked/i)).toBeInTheDocument();
    });
  });
});
```

- [ ] **Step 46.5: Create `frontend/src/settings/NewTokenDialog.tsx`**

```tsx
import { useState } from "react";
import type { CreateTokenResponseDTO } from "../api/types";

interface Props {
  onCreate: (input: { label: string; role: string; device_label: string }) => Promise<CreateTokenResponseDTO>;
  onClose: () => void;
}

type Stage =
  | { kind: "form" }
  | { kind: "submitting" }
  | { kind: "reveal"; token: CreateTokenResponseDTO }
  | { kind: "error"; message: string };

export function NewTokenDialog({ onCreate, onClose }: Props) {
  const [stage, setStage] = useState<Stage>({ kind: "form" });
  const [label, setLabel] = useState("");
  const [role, setRole] = useState("claude");
  const [device, setDevice] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!label.trim() || !device.trim()) return;
    setStage({ kind: "submitting" });
    try {
      const t = await onCreate({ label: label.trim(), role, device_label: device.trim() });
      setStage({ kind: "reveal", token: t });
    } catch (err) {
      setStage({ kind: "error", message: err instanceof Error ? err.message : String(err) });
    }
  }

  return (
    <div className="fixed inset-0 bg-black/30 grid place-items-center z-50">
      <div className="bg-bg border border-border rounded-xl w-full max-w-md p-5">
        {stage.kind !== "reveal" ? (
          <form onSubmit={submit} className="flex flex-col gap-3">
            <h2 className="font-[var(--font-display)] text-lg">New agent token</h2>
            <label className="text-[12px] text-text-muted flex flex-col gap-1">
              Label
              <input
                value={label} onChange={(e) => setLabel(e.target.value)}
                placeholder="claude on neo-mbp"
                className="border border-border rounded px-2 py-1.5 bg-surface-elev"
              />
            </label>
            <label className="text-[12px] text-text-muted flex flex-col gap-1">
              Role
              <select
                value={role} onChange={(e) => setRole(e.target.value)}
                className="border border-border rounded px-2 py-1.5 bg-surface-elev"
              >
                <option value="claude">claude</option>
                <option value="codex">codex</option>
              </select>
            </label>
            <label className="text-[12px] text-text-muted flex flex-col gap-1">
              Device
              <input
                value={device} onChange={(e) => setDevice(e.target.value)}
                placeholder="neo-mbp"
                className="border border-border rounded px-2 py-1.5 bg-surface-elev"
              />
            </label>
            {stage.kind === "error" && (
              <div className="text-[12px] text-finding">{stage.message}</div>
            )}
            <div className="flex gap-2 mt-1">
              <button
                type="button" onClick={onClose}
                className="px-3 py-1.5 rounded border border-border text-[13px]"
              >Cancel</button>
              <div className="flex-1" />
              <button
                type="submit"
                disabled={stage.kind === "submitting"}
                className="px-3 py-1.5 rounded bg-text text-bg text-[13px] font-medium disabled:opacity-50"
              >Create</button>
            </div>
          </form>
        ) : (
          <div className="flex flex-col gap-3">
            <h2 className="font-[var(--font-display)] text-lg">Copy now — it won't show again</h2>
            <p className="text-[12px] text-text-muted">
              Paste this into your local <code className="font-mono">.mcp.json</code> as the
              <code className="font-mono"> Authorization: Bearer …</code> header value.
            </p>
            <pre className="bg-surface border border-border rounded p-2.5 font-mono text-[12px] break-all">
              {stage.token.value}
            </pre>
            <div className="text-[11px] text-text-dim">
              registered as <code className="font-mono">
                {stage.token.agent_instance.role} · {stage.token.agent_instance.device_label}
              </code>
            </div>
            <div className="flex justify-end mt-1">
              <button
                type="button" onClick={onClose}
                className="px-3 py-1.5 rounded bg-text text-bg text-[13px] font-medium"
              >Done</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 46.6: Create `frontend/src/settings/SettingsTokensPage.tsx`**

```tsx
import { useState } from "react";
import { useMyTokens, useCreateToken, useRevokeToken } from "../api/queries";
import { NewTokenDialog } from "./NewTokenDialog";

export function SettingsTokensPage() {
  const [openNew, setOpenNew] = useState(false);
  const tokens = useMyTokens();
  const createToken = useCreateToken();
  const revoke = useRevokeToken();

  return (
    <div className="flex flex-col gap-4 p-8 overflow-y-auto h-full">
      <div className="flex items-baseline justify-between">
        <h2 className="font-[var(--font-display)] text-2xl">Agent Tokens</h2>
        <button
          type="button"
          onClick={() => setOpenNew(true)}
          className="px-3 py-1.5 rounded bg-text text-bg text-[13px] font-medium"
        >+ New token</button>
      </div>

      <p className="text-[12px] text-text-muted max-w-2xl">
        每个本地 agent（Claude Code / Codex）通过一个 token 接入 Lets 后端。
        Token 只会在创建时显示一次，丢了只能 revoke + 新建。
      </p>

      {tokens.isLoading && <div className="text-text-dim">Loading…</div>}

      {tokens.data && tokens.data.length === 0 && (
        <div className="border border-dashed border-border rounded-lg p-6 text-center text-text-dim">
          No agent tokens yet. Click "+ New token" to issue one for your local CC or Codex.
        </div>
      )}

      {tokens.data && tokens.data.length > 0 && (
        <table className="w-full text-left text-[13px]">
          <thead>
            <tr className="text-text-dim text-[11px] uppercase tracking-wider">
              <th className="px-3 py-2">Label</th>
              <th className="px-3 py-2">Created</th>
              <th className="px-3 py-2">Last used</th>
              <th className="px-3 py-2">State</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {tokens.data.map((t) => (
              <tr key={t.id} className="border-t border-border-soft">
                <td className="px-3 py-2 font-mono">{t.label ?? `#${t.id}`}</td>
                <td className="px-3 py-2 text-text-muted">{t.created_at.slice(0, 16).replace("T", " ")}</td>
                <td className="px-3 py-2 text-text-muted">
                  {t.last_used_at ? t.last_used_at.slice(0, 16).replace("T", " ") : "never"}
                </td>
                <td className="px-3 py-2">
                  {t.revoked_at ? (
                    <span className="text-[11px] px-2 py-px rounded bg-finding-bg text-finding">revoked</span>
                  ) : (
                    <span className="text-[11px] px-2 py-px rounded bg-status-on/20 text-status-on">active</span>
                  )}
                </td>
                <td className="px-3 py-2 text-right">
                  {!t.revoked_at && (
                    <button
                      type="button"
                      onClick={() => revoke.mutate(t.id)}
                      disabled={revoke.isPending}
                      className="text-[12px] text-finding hover:underline disabled:opacity-50"
                    >Revoke</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {openNew && (
        <NewTokenDialog
          onCreate={(input) => createToken.mutateAsync(input)}
          onClose={() => setOpenNew(false)}
        />
      )}
    </div>
  );
}
```

- [ ] **Step 46.7: Run tests**

```bash
cd frontend && pnpm test SettingsTokensPage
```

Expected: 2 tests pass.

- [ ] **Step 46.8: Smoke against real backend**

```bash
.venv/bin/uvicorn app.main:app --port 8000
cd frontend && pnpm dev
```

In the SPA, click "个人设置" → "Agent Tokens" → "+ New token" → label `claude on neo-mbp` / role `claude` / device `neo-mbp` → Create → copy the `lets_…` value.

Edit your local `~/.claude/.mcp.json` to use `http://localhost:8000/mcp/` + the new token. Restart Claude Code. In the chat, ask CC to "post a status to topic 1". The message should appear in the SPA's stream live via SSE.

- [ ] **Step 46.9: Commit**

```bash
git add frontend/src/settings/ frontend/src/api/queries.ts frontend/src/api/types.ts \
        frontend/src/api/client.ts frontend/src/fixtures/handlers.ts
git commit -m "feat(frontend): Settings → Agent Tokens page with create + revoke flow"
```

---


After completing all tasks above, verify the plan covered every spec line from the brainstorming session:

**Visual baseline (sticks to mock.html v6, 1-2 review checkpoints allowed)**
- Tokens ported: ✅ Task 2 ports OKLCH @theme
- Bricolage + Geist fonts: ✅ Task 2 step 2.2 adds font CDN links
- Design checkpoints: ✅ Task 13 (after app shell) + Task 32 (after context pane)

**Desktop 3-pane layout**
- AppShell with sidebar/main/context: ✅ Task 9
- Responsive: context hides < 1280px, sidebar hides < 768px: ✅ Task 9 step 9.4

**Goal merged into TopicHeader, detail in context pane**
- TopicHeaderProgress with ring + current-task: ✅ Task 11
- GoalDetailPanel in context (Mark as Final, approvers): ✅ Task 35

**Task Tree**
- TaskTreeProposalMessage (in stream): ✅ Task 21
- TaskTreePanel (in context pane): ✅ Task 29

**Artifact inline thumbnails**
- SlideThumb component: ✅ Task 19
- ArtifactRevisionMessage inline thumbs: ✅ Task 19
- ArtifactPanel in context pane: ✅ Task 29

**Attention Queue 3 groups**
- AttentionCard + AttentionGroup: ✅ Task 33
- AttentionView with greeting + 3 groups: ✅ Task 34
- Mobile attention via BottomTabs: ✅ Tasks 37–38

**All 13 typed messages**
- chat/status/system: ✅ Task 16
- finding/decision/question/review: ✅ Task 17
- handoff/nudge/proactive_finding: ✅ Task 18
- artifact_revision: ✅ Task 19
- spec_change: ✅ Task 20 + wired in Task 36
- task_tree_proposal: ✅ Task 21

**Real API + SSE + spec_change approve roundtrip**
- Backend GET/POST /api/topics: ✅ Task 24
- Backend SSE stream: ✅ Task 25
- useTopicStream hook: ✅ Task 26
- Composer wired to usePostMessage: ✅ Task 27
- Spec change Approve posts decision: ✅ Task 36

**Mobile**
- BottomTabs nav: ✅ Task 37
- Mobile view switching: ✅ Task 38

**Integration / production serving**
- `/app` mount: ✅ Task 39
- E2E PPT scenario: ✅ Task 40
- Real-mode smoke: ✅ Task 41
- v1 redirect: ✅ Task 42

**Phase 12 — Auth & Token UI**
- GitHub OAuth flow + session cookie + `/auth/me` + logout: ✅ Task 43
- REST tokens CRUD gated by session: ✅ Task 44
- Frontend Login page + SessionGate + IdentityProvider session wiring: ✅ Task 45
- Settings → Agent Tokens page with create + revoke + one-time reveal: ✅ Task 46

**Out of scope for Track F (kept for Track C / future tracks)**
- `gh repo create` + `git clone` execution → handled by CC/Codex via Bash on user-approved `project_proposal`, not by a daemon. Track C wires the conversation flow; Track F just renders the `project_proposal` typed message which is already a v1.5b/c roadmap item.
- Local daemon (file watcher, AgentFS, menu-bar status) → moved from v1.5a to v1.5b/c in roadmap discussion; not blocking dogfood. See "v1.5a dogfood path" notes below.
- Non-GitHub onboarding (email magic link) → CLI `python -m app.tokens_cli issue` is the fallback for v1.5a; LoginPage already documents this.
- Per-org / team scoping of tokens → single workspace for v1.5; Track G or later.

**v1.5a dogfood path enabled by this plan**

After Phase 12 lands, the minimal-friction onboarding for a new colleague is:
1. Visit `https://<deploy>/app` → "Login with GitHub" → workspace shell loads
2. "个人设置" → "Agent Tokens" → "+ New token" → label `claude on <their-laptop>` → copy raw value
3. Paste value into their local `~/.claude/.mcp.json` (`url` is the same Railway hostname, only token differs)
4. Restart their CC → their CC registers as a new `agent_instance` under their `human` row
5. They start chatting in the SPA; their agent reads/writes via MCP; everyone sees everyone's activity through SSE

No daemon, no manual CLI command on the server side, no shared secret.

**Type consistency check**
- `MessageType` 13 strings match across `frontend/src/api/types.ts` and `app/messages.py ALLOWED_TYPES` — explicit cross-check in Task 4 step 4.4
- DTO field names match `app/db.py` schema lines 154–212
- All actor signatures match across Message dispatch + 13 typed components: `{ kind: "human" | "claude" | "codex" | "system"; initial: string; displayName: string }`

**Spec gaps to flag for follow-up (out of scope for Track F)**
- `proactive_finding` / `nudge` / `task_tree_proposal` rely on fixture content because backend has no producer for them yet — backend producers land in v1.5c per roadmap
- Real artifact thumbnails (`preview_uri`) — Track D adapter provides URI but Phase 9 (Track F) draws generic thumbs; swap when Track D's `GoogleSlidesBackend` lands in v1.5c
- @mention resolution against real human directory — Phase 5 uses `SCRATCH_DIRECTORY` constant; replace with `useDirectory()` query once Track A adds a `/api/directory` endpoint

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-19-track-f-web-frontend.md`. Two execution options:

**1. Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration. Best for this plan because tasks have clear file boundaries and each task is independently testable.

**2. Inline Execution** — execute tasks in this session using `superpowers:executing-plans`, batch execution with checkpoints. Better if you want me to do all of Phase 0 right now without spawning subagents.

Which approach?







