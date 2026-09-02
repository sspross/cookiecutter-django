/**
 * TanStack Query hook for `/api/me` — the current user.
 *
 * Per-user boot data goes through the typed API, read like any other server
 * state. See ADR-0006.
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
