/**
 * React Query hooks for the Task resource.
 *
 * The list endpoint is filterable by project so the project detail page
 * can fetch just its tasks. Mutations invalidate the parent project's
 * task list and (where it matters) the all-tasks list, since priority/
 * status changes might shift global counts in the future.
 */

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { components } from "../../types/api";

export type Task = components["schemas"]["TaskOut"];
export type TaskIn = components["schemas"]["TaskIn"];
export type TaskPatch = components["schemas"]["TaskPatch"];
export type TaskStatus = Task["status"];
export type TaskPriority = Task["priority"];

export interface TaskListPage {
  items: Task[];
  count: number;
}

export interface TaskListQuery {
  project?: number;
  status?: TaskStatus;
  priority?: TaskPriority;
  due_from?: string;
  due_to?: string;
  limit: number;
  offset: number;
}

export const tasksKeys = {
  all: ["tasks"] as const,
  lists: () => [...tasksKeys.all, "list"] as const,
  list: (q: TaskListQuery) => [...tasksKeys.lists(), q] as const,
  byProject: (projectId: number) =>
    [...tasksKeys.lists(), { project: projectId }] as const,
  details: () => [...tasksKeys.all, "detail"] as const,
  detail: (id: number) => [...tasksKeys.details(), id] as const,
};

export function useTasksList(query: TaskListQuery) {
  return useQuery({
    queryKey: tasksKeys.list(query),
    queryFn: async (): Promise<TaskListPage> => {
      const { data, error } = await api.GET("/api/example/tasks", {
        params: { query },
      });
      if (error) throw error;
      if (!data) throw new Error("No data returned from tasks list");
      return data as TaskListPage;
    },
  });
}

export function useTask(id: number) {
  return useQuery({
    queryKey: tasksKeys.detail(id),
    queryFn: async (): Promise<Task> => {
      const { data, error } = await api.GET("/api/example/tasks/{task_id}", {
        params: { path: { task_id: id } },
      });
      if (error) throw error;
      if (!data) throw new Error("No data returned for task");
      return data;
    },
  });
}

export function useCreateTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: TaskIn): Promise<Task> => {
      const { data, error } = await api.POST("/api/example/tasks", { body });
      if (error) throw error;
      if (!data) throw new Error("No data returned from create task");
      return data;
    },
    onSuccess: (created) => {
      // Invalidate the all-tasks list and the parent project's task list
      // so the new row shows up immediately in either view.
      qc.invalidateQueries({ queryKey: tasksKeys.lists() });
      qc.invalidateQueries({
        queryKey: tasksKeys.byProject(created.project_id),
      });
    },
  });
}

export function useUpdateTask(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: TaskPatch): Promise<Task> => {
      const { data, error } = await api.PATCH(
        "/api/example/tasks/{task_id}",
        { params: { path: { task_id: id } }, body },
      );
      if (error) throw error;
      if (!data) throw new Error("No data returned from update task");
      return data;
    },
    onMutate: async (body) => {
      await qc.cancelQueries({ queryKey: tasksKeys.detail(id) });
      const previous = qc.getQueryData<Task>(tasksKeys.detail(id));
      if (previous) {
        const merged: Task = { ...previous };
        for (const key of [
          "title",
          "description",
          "status",
          "priority",
        ] as const) {
          const value = body[key];
          if (value != null) {
            (merged[key] as unknown) = value;
          }
        }
        qc.setQueryData<Task>(tasksKeys.detail(id), merged);
      }
      return { previous };
    },
    onError: (_err, _body, context) => {
      if (context?.previous) {
        qc.setQueryData(tasksKeys.detail(id), context.previous);
      }
    },
    onSettled: (data) => {
      qc.invalidateQueries({ queryKey: tasksKeys.lists() });
      qc.invalidateQueries({ queryKey: tasksKeys.detail(id) });
      if (data) {
        qc.invalidateQueries({
          queryKey: tasksKeys.byProject(data.project_id),
        });
      }
    },
  });
}

export function useDeleteTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
    }: {
      id: number;
      projectId: number;
    }): Promise<void> => {
      const { error } = await api.DELETE("/api/example/tasks/{task_id}", {
        params: { path: { task_id: id } },
      });
      if (error) throw error;
    },
    onMutate: async ({ id }) => {
      await qc.cancelQueries({ queryKey: tasksKeys.lists() });
      const lists = qc.getQueriesData<TaskListPage>({
        queryKey: tasksKeys.lists(),
      });
      for (const [key, page] of lists) {
        if (!page) continue;
        qc.setQueryData<TaskListPage>(key, {
          ...page,
          items: page.items.filter((t) => t.id !== id),
          count: Math.max(0, page.count - 1),
        });
      }
      return { lists };
    },
    onError: (_err, _variables, context) => {
      if (!context?.lists) return;
      for (const [key, page] of context.lists) {
        qc.setQueryData(key, page);
      }
    },
    onSettled: (_data, _err, { projectId }) => {
      qc.invalidateQueries({ queryKey: tasksKeys.lists() });
      qc.invalidateQueries({ queryKey: tasksKeys.byProject(projectId) });
    },
  });
}
