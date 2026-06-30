import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router";

import "./spa/index.css";
import { App } from "./spa/App";

// Pages that share the bundle only for CSS (login, admin error pages)
// will not have an `#app` mount node — bail early so they pick up
// styling without paying for React boot.
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

  // `projectName` is a build-time constant server-rendered onto the mount
  // node. Per-user data (username) is fetched from the typed `/api/me`.
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
