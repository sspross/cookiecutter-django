/**
 * React Query hooks for the Project resource.
 *
 * Mirrors the Tag pattern from `resources/tags`. Mutations invalidate the
 * project list and (when relevant) the tag list, since changing a project
 * touches the tag→project related set as well.
 */

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { api } from "@/lib/api";
import { tagsKeys } from "@/resources/tags";
import type { components } from "../../types/api";

export type Project = components["schemas"]["ProjectOut"];
export type ProjectIn = components["schemas"]["ProjectIn"];
export type ProjectPatch = components["schemas"]["ProjectPatch"];
export type ProjectStatus = Project["status"];

export interface ProjectListPage {
  items: Project[];
  count: number;
}

export interface ProjectListQuery {
  title?: string;
  status?: ProjectStatus;
  tag?: number;
  limit: number;
  offset: number;
}

export const projectsKeys = {
  all: ["projects"] as const,
  lists: () => [...projectsKeys.all, "list"] as const,
  list: (q: ProjectListQuery) => [...projectsKeys.lists(), q] as const,
  details: () => [...projectsKeys.all, "detail"] as const,
  detail: (id: number) => [...projectsKeys.details(), id] as const,
};

export function useProjectsList(query: ProjectListQuery) {
  return useQuery({
    queryKey: projectsKeys.list(query),
    queryFn: async (): Promise<ProjectListPage> => {
      const { data, error } = await api.GET("/api/example/projects", {
        params: { query },
      });
      if (error) throw error;
      if (!data) throw new Error("No data returned from projects list");
      return data as ProjectListPage;
    },
  });
}

export function useProject(id: number) {
  return useQuery({
    queryKey: projectsKeys.detail(id),
    queryFn: async (): Promise<Project> => {
      const { data, error } = await api.GET(
        "/api/example/projects/{project_id}",
        { params: { path: { project_id: id } } },
      );
      if (error) throw error;
      if (!data) throw new Error("No data returned for project");
      return data;
    },
  });
}

export function useCreateProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: ProjectIn): Promise<Project> => {
      const { data, error } = await api.POST("/api/example/projects", {
        body,
      });
      if (error) throw error;
      if (!data) throw new Error("No data returned from create project");
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: projectsKeys.lists() });
      qc.invalidateQueries({ queryKey: tagsKeys.lists() });
    },
  });
}

export function useUpdateProject(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: ProjectPatch): Promise<Project> => {
      const { data, error } = await api.PATCH(
        "/api/example/projects/{project_id}",
        { params: { path: { project_id: id } }, body },
      );
      if (error) throw error;
      if (!data) throw new Error("No data returned from update project");
      return data;
    },
    onMutate: async (body) => {
      await qc.cancelQueries({ queryKey: projectsKeys.detail(id) });
      const previous = qc.getQueryData<Project>(projectsKeys.detail(id));
      if (previous) {
        const merged: Project = {
          ...previous,
          ...(body.title != null ? { title: body.title } : {}),
          ...(body.description != null
            ? { description: body.description }
            : {}),
          ...(body.status != null ? { status: body.status } : {}),
        };
        qc.setQueryData<Project>(projectsKeys.detail(id), merged);
      }
      return { previous };
    },
    onError: (_err, _body, context) => {
      if (context?.previous) {
        qc.setQueryData(projectsKeys.detail(id), context.previous);
      }
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: projectsKeys.lists() });
      qc.invalidateQueries({ queryKey: projectsKeys.detail(id) });
      qc.invalidateQueries({ queryKey: tagsKeys.lists() });
    },
  });
}

export function useDeleteProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number): Promise<void> => {
      const { error } = await api.DELETE(
        "/api/example/projects/{project_id}",
        { params: { path: { project_id: id } } },
      );
      if (error) throw error;
    },
    onMutate: async (id) => {
      await qc.cancelQueries({ queryKey: projectsKeys.lists() });
      const lists = qc.getQueriesData<ProjectListPage>({
        queryKey: projectsKeys.lists(),
      });
      for (const [key, page] of lists) {
        if (!page) continue;
        qc.setQueryData<ProjectListPage>(key, {
          ...page,
          items: page.items.filter((p) => p.id !== id),
          count: Math.max(0, page.count - 1),
        });
      }
      return { lists };
    },
    onError: (_err, _id, context) => {
      if (!context?.lists) return;
      for (const [key, page] of context.lists) {
        qc.setQueryData(key, page);
      }
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: projectsKeys.lists() });
    },
  });
}
