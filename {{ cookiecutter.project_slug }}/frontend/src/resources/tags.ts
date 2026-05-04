/**
 * React Query hooks for the Tag resource.
 *
 * One small hand-written module per resource. The hooks consume the typed
 * `openapi-fetch` client; mutations invalidate the right queries and apply
 * optimistic updates where it improves perceived latency.
 */

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { components } from "../../types/api";

export type Tag = components["schemas"]["TagOut"];
export type TagIn = components["schemas"]["TagIn"];
export type TagPatch = components["schemas"]["TagPatch"];

export interface TagListPage {
  items: Tag[];
  count: number;
}

export interface TagListQuery {
  name?: string;
  slug?: string;
  limit: number;
  offset: number;
}

export const tagsKeys = {
  all: ["tags"] as const,
  lists: () => [...tagsKeys.all, "list"] as const,
  list: (q: TagListQuery) => [...tagsKeys.lists(), q] as const,
  details: () => [...tagsKeys.all, "detail"] as const,
  detail: (id: number) => [...tagsKeys.details(), id] as const,
};

export function useTagsList(query: TagListQuery) {
  return useQuery({
    queryKey: tagsKeys.list(query),
    queryFn: async (): Promise<TagListPage> => {
      const { data, error } = await api.GET("/api/example/tags", {
        params: { query },
      });
      if (error) throw error;
      if (!data) throw new Error("No data returned from tags list");
      return data as TagListPage;
    },
  });
}

export function useTag(id: number) {
  return useQuery({
    queryKey: tagsKeys.detail(id),
    queryFn: async (): Promise<Tag> => {
      const { data, error } = await api.GET("/api/example/tags/{tag_id}", {
        params: { path: { tag_id: id } },
      });
      if (error) throw error;
      if (!data) throw new Error("No data returned for tag");
      return data;
    },
  });
}

export function useCreateTag() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: TagIn): Promise<Tag> => {
      const { data, error } = await api.POST("/api/example/tags", { body });
      if (error) throw error;
      if (!data) throw new Error("No data returned from create tag");
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: tagsKeys.lists() });
    },
  });
}

export function useUpdateTag(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: TagPatch): Promise<Tag> => {
      const { data, error } = await api.PATCH("/api/example/tags/{tag_id}", {
        params: { path: { tag_id: id } },
        body,
      });
      if (error) throw error;
      if (!data) throw new Error("No data returned from update tag");
      return data;
    },
    onMutate: async (body) => {
      await qc.cancelQueries({ queryKey: tagsKeys.detail(id) });
      const previous = qc.getQueryData<Tag>(tagsKeys.detail(id));
      if (previous) {
        const merged: Tag = {
          ...previous,
          ...(body.name != null ? { name: body.name } : {}),
          ...(body.slug != null ? { slug: body.slug } : {}),
        };
        qc.setQueryData<Tag>(tagsKeys.detail(id), merged);
      }
      return { previous };
    },
    onError: (_err, _body, context) => {
      if (context?.previous) {
        qc.setQueryData(tagsKeys.detail(id), context.previous);
      }
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: tagsKeys.lists() });
      qc.invalidateQueries({ queryKey: tagsKeys.detail(id) });
    },
  });
}

export function useDeleteTag() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number): Promise<void> => {
      const { error } = await api.DELETE("/api/example/tags/{tag_id}", {
        params: { path: { tag_id: id } },
      });
      if (error) throw error;
    },
    onMutate: async (id) => {
      await qc.cancelQueries({ queryKey: tagsKeys.lists() });
      const lists = qc.getQueriesData<TagListPage>({
        queryKey: tagsKeys.lists(),
      });
      for (const [key, page] of lists) {
        if (!page) continue;
        qc.setQueryData<TagListPage>(key, {
          ...page,
          items: page.items.filter((t) => t.id !== id),
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
      qc.invalidateQueries({ queryKey: tagsKeys.lists() });
    },
  });
}
