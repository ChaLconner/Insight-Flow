import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { favoritesApi, type ToggleFavoriteResponse } from "@/lib/api-endpoints";
import { useAuthStore } from "@/stores/auth-store";
import { toast } from "sonner";
import { getErrorMessage } from "@/lib/error-utils";

/**
 * Hook for fetching user's favorite project IDs
 */
export function useFavoriteIds() {
  const { user } = useAuthStore();

  return useQuery({
    queryKey: ["favorites"],
    queryFn: async () => {
      const projectIds = await favoritesApi.getFavoriteIds();
      return new Set(projectIds);
    },
    enabled: !!user,
    staleTime: 60 * 1000, // 1 minute
    // Fallback to empty set on error
    placeholderData: () => new Set<string>(),
  });
}

/**
 * Hook for toggling favorite status of a project
 */
export function useToggleFavorite() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (projectId: string) => {
      return await favoritesApi.toggleFavorite(projectId);
    },
    onMutate: async (projectId) => {
      // Optimistic update
      await queryClient.cancelQueries({ queryKey: ["favorites"] });
      const previousFavorites = queryClient.getQueryData<Set<string>>(["favorites"]);

      queryClient.setQueryData<Set<string>>(["favorites"], (old) => {
        const newSet = new Set(old);
        if (newSet.has(projectId)) {
          newSet.delete(projectId);
        } else {
          newSet.add(projectId);
        }
        return newSet;
      });

      return { previousFavorites };
    },
    onError: (err, projectId, context) => {
      // Rollback on error
      queryClient.setQueryData(["favorites"], context?.previousFavorites);
      toast.error("Failed to update favorite", {
        description: getErrorMessage(err),
      });
    },
    onSuccess: (data: ToggleFavoriteResponse) => {
      if (data.isFavorite) {
        toast.success("Added to Favorites", {
          description: data.message,
        });
      } else {
        toast.success("Removed from Favorites", {
          description: data.message,
        });
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["favorites"] });
    },
  });
}

/**
 * Hook for adding a project to favorites (explicit add)
 */
export function useAddFavorite() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (projectId: string) => {
      return await favoritesApi.addFavorite(projectId);
    },
    onSuccess: (data: ToggleFavoriteResponse) => {
      queryClient.invalidateQueries({ queryKey: ["favorites"] });
      toast.success("Added to Favorites", {
        description: data.message,
      });
    },
    onError: (err) => {
      toast.error("Failed to add to favorites", {
        description: getErrorMessage(err),
      });
    },
  });
}

/**
 * Hook for removing a project from favorites
 */
export function useRemoveFavorite() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (projectId: string) => {
      await favoritesApi.removeFavorite(projectId);
      return projectId;
    },
    onMutate: async (projectId) => {
      await queryClient.cancelQueries({ queryKey: ["favorites"] });
      const previousFavorites = queryClient.getQueryData<Set<string>>(["favorites"]);

      queryClient.setQueryData<Set<string>>(["favorites"], (old) => {
        const newSet = new Set(old);
        newSet.delete(projectId);
        return newSet;
      });

      return { previousFavorites };
    },
    onError: (err, projectId, context) => {
      queryClient.setQueryData(["favorites"], context?.previousFavorites);
      toast.error("Failed to remove from favorites", {
        description: getErrorMessage(err),
      });
    },
    onSuccess: () => {
      toast.success("Removed from Favorites");
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["favorites"] });
    },
  });
}
