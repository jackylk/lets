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
