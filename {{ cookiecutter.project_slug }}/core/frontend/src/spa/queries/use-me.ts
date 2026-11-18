import { useQuery } from "@tanstack/react-query";
import { apiClient, requireData } from "@/api/client";
import type { Me } from "@/api/types";

export const meKeys = {
  me: () => ["me"] as const,
};

export function useMe() {
  return useQuery<Me>({
    queryKey: meKeys.me(),
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/me", {});
      if (error) throw error;
      return requireData(data, "GET /api/me");
    },
  });
}
