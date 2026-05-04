import { useQuery } from "@tanstack/react-query";
import {
  createRootRoute,
  createRoute,
  createRouter,
  Outlet,
} from "@tanstack/react-router";

import { api } from "@/lib/api";
import { HealthPage } from "@/routes/health";
import { ProjectDetailPage } from "@/routes/project-detail";
import {
  ProjectsListPage,
  projectsSearchSchema,
} from "@/routes/projects-list";
import { TagsPage, tagsSearchSchema } from "@/routes/tags";

function RootComponent() {
  // Prime the `csrftoken` cookie once on app boot. Mutations (POST/PATCH/DELETE)
  // need it on the very first request, regardless of which route the SPA
  // boots into. The HTTP roundtrip is small and only happens once because
  // React Query caches the result with a long stale time.
  useQuery({
    queryKey: ["bootstrap-config"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/config");
      if (error) throw error;
      return data;
    },
    staleTime: Infinity,
  });
  return <Outlet />;
}

const rootRoute = createRootRoute({
  component: RootComponent,
});

const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  component: HealthPage,
});

const tagsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/tags",
  validateSearch: tagsSearchSchema,
  component: TagsPage,
});

const projectsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/projects",
  validateSearch: projectsSearchSchema,
  component: ProjectsListPage,
});

const projectDetailRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/projects/$projectId",
  component: ProjectDetailPage,
});

const routeTree = rootRoute.addChildren([
  indexRoute,
  tagsRoute,
  projectsRoute,
  projectDetailRoute,
]);

export const router = createRouter({
  routeTree,
  defaultPreload: "intent",
});

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
