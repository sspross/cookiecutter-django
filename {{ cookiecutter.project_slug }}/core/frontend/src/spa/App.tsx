import { Route, Routes } from "react-router";
import { AppShell } from "@/components/layout/app-shell";
import { ApiAccessRoute } from "@/routes/api-access";
import { DashboardRoute } from "@/routes/index";

interface AppProps {
  projectName: string;
  username?: string;
}

export function App({ projectName, username }: AppProps) {
  return (
    <AppShell projectName={projectName} username={username}>
      <Routes>
        <Route path="/" element={<DashboardRoute />} />
        <Route path="/api-access" element={<ApiAccessRoute />} />
      </Routes>
    </AppShell>
  );
}
