/**
 * TanStack Query hook for `/api/me` — the current user.
 *
 * Per-user boot data lives behind the typed API (ADR-0006), not an inlined
 * `window` global, so the SPA reads it the same way it reads any other
 * server state.
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient, type Me } from "@/api/client";

export const meKeys = {
  me: () => ["me"] as const,
};

export function useMe() {
  return useQuery<Me>({
    queryKey: meKeys.me(),
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/me", {});
      if (error) throw error;
      return data!;
    },
  });
}
