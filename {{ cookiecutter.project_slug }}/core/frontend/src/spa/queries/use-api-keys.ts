import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  type ApiKey,
  type ApiKeyCreateIn,
  type ApiKeyMintOut,
  apiClient,
  requireData,
} from "@/api/client";

export const apiKeyKeys = {
  list: () => ["api-keys", "list"] as const,
};

export function useApiKeys() {
  return useApiKeysList();
}

export function useApiKeysList() {
  return useQuery<ApiKey[]>({
    queryKey: apiKeyKeys.list(),
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/api-keys/", {});
      if (error) throw error;
      return requireData(data, "GET /api/api-keys/");
    },
  });
}

export function useMintApiKey() {
  const queryClient = useQueryClient();
  return useMutation<ApiKeyMintOut, Error, ApiKeyCreateIn>({
    mutationFn: async (payload) => {
      const { data, error, response } = await apiClient.POST("/api/api-keys/", {
        body: payload,
      });
      if (error || !response.ok) {
        throw new Error(`Mint failed: ${response.status}`);
      }
      return requireData(data, "POST /api/api-keys/");
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: apiKeyKeys.list() });
    },
  });
}

export function useRevokeApiKey() {
  const queryClient = useQueryClient();
  return useMutation<ApiKey, Error, number>({
    mutationFn: async (id) => {
      const { data, error, response } = await apiClient.POST(
        "/api/api-keys/{api_key_id}/revoke/",
        { params: { path: { api_key_id: id } } },
      );
      if (error || !response.ok) {
        throw new Error(`Revoke failed: ${response.status}`);
      }
      return requireData(data, "POST /api/api-keys/{api_key_id}/revoke/");
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: apiKeyKeys.list() });
    },
  });
}
