import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router";

import "./spa/index.css";
import { App } from "./spa/App";

// The login page loads this bundle for its CSS and has no `#app` node.
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
