import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router";

import "./spa/index.css";
import { App } from "./spa/App";

// Pages that load the bundle only for its CSS (login, admin error pages) have
// no `#app` node — bail before React boots.
const mountNode = document.getElementById("app");
if (mountNode) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        refetchOnWindowFocus: false,
        staleTime: 1000,
      },
    },
  });

  // Build-time constant, server-rendered onto the mount node. Per-user data
  // goes through `/api/me` instead. See ADR-0006.
  const projectName = mountNode.dataset.projectName ?? "";

  ReactDOM.createRoot(mountNode).render(
    <React.StrictMode>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <App projectName={projectName} />
        </BrowserRouter>
      </QueryClientProvider>
    </React.StrictMode>,
  );
}
