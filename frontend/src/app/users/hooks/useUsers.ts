"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import type { User } from "@/types";
import type { UserRole } from "@/types";
import { useAuthStore } from "@/stores/auth-store";
import { usersApi } from "@/lib/api-endpoints";
import { toast } from "sonner";
import { getErrorMessage } from "@/lib/error-utils";
import type { UserStatsData } from "../types";
import { DEFAULT_USER_STATS } from "../types";

interface UseUsersOptions {
  pageSize?: number;
  debounceMs?: number;
}

interface UseUsersReturn {
  // Data
  users: User[];
  stats: UserStatsData;

  // Loading states
  loading: boolean;
  refreshing: boolean;
  error: string | null;
  dataFetched: boolean;

  // Filters
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  debouncedSearchQuery: string;
  roleFilter: UserRole | "all";
  setRoleFilter: (role: UserRole | "all") => void;
  statusFilter: "all" | "active" | "inactive";
  setStatusFilter: (status: "all" | "active" | "inactive") => void;

  // Pagination
  page: number;
  setPage: (page: number) => void;
  pageSize: number;
  hasMore: boolean;

  // Actions
  refresh: () => void;
  loadUsers: (forceRefresh?: boolean) => Promise<void>;
}

/**
 * useUsers - Custom hook for managing users state and operations
 * Handles fetching, filtering, pagination, and state management
 */
export function useUsers(options: UseUsersOptions = {}): UseUsersReturn {
  const { pageSize = 10, debounceMs = 300 } = options;

  // Data state
  const [users, setUsers] = useState<User[]>([]);
  const [stats, setStats] = useState<UserStatsData>(DEFAULT_USER_STATS);

  // Loading states
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dataFetched, setDataFetched] = useState(false);

  // Filter state
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedSearchQuery, setDebouncedSearchQuery] = useState("");
  const [roleFilter, setRoleFilter] = useState<UserRole | "all">("all");
  const [statusFilter, setStatusFilter] = useState<
    "all" | "active" | "inactive"
  >("all");

  // Pagination state
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);

  // Refs
  const searchDebounceRef = useRef<NodeJS.Timeout | null>(null);
  const isLoadingRef = useRef(false);
  const lastLoadTime = useRef<number>(0);

  const { isAuthenticated, isLoading } = useAuthStore();

  // Fetch stats
  const fetchStats = useCallback(async () => {
    try {
      const statsData = await usersApi.getStats();
      setStats(statsData);
    } catch (err) {
      console.error("Error loading stats:", err);
    }
  }, []);

  // Load users
  const loadUsers = useCallback(
    async (forceRefresh = false) => {
      if (!isAuthenticated) {
        return;
      }

      const now = Date.now();
      if (!forceRefresh && now - lastLoadTime.current < 500 && dataFetched) {
        return;
      }

      if (isLoadingRef.current) {
        return;
      }

      try {
        isLoadingRef.current = true;
        lastLoadTime.current = now;

        if (forceRefresh) {
          setRefreshing(true);
        } else {
          setLoading(true);
        }
        setError(null);

        const skip = (page - 1) * pageSize;

        try {
          const [usersData] = await Promise.all([
            usersApi.searchUsers(
              debouncedSearchQuery,
              skip,
              pageSize,
              roleFilter === "all" ? undefined : roleFilter,
              statusFilter === "all" ? undefined : statusFilter,
            ),
            forceRefresh || !dataFetched ? fetchStats() : Promise.resolve(),
          ]);

          const userList = Array.isArray(usersData)
            ? usersData
            : ((usersData as Record<string, unknown>).data as User[]) ?? [];
          setUsers(userList);
          setHasMore(userList.length === pageSize);
        } catch (apiError) {
          console.error("API issue:", apiError);
          setUsers([]);
        }

        setDataFetched(true);
      } catch (err) {
        console.error("Error loading users:", err);
        setError("Failed to load users");
        toast.error("Failed to load users", {
          description: getErrorMessage(err),
        });
      } finally {
        isLoadingRef.current = false;
        setLoading(false);
        setRefreshing(false);
      }
    },
    [
      isAuthenticated,
      dataFetched,
      page,
      pageSize,
      debouncedSearchQuery,
      roleFilter,
      statusFilter,
      fetchStats,
    ],
  );

  // Initial load
  useEffect(() => {
    if (isLoading) {
      return;
    }
    if (isAuthenticated) {
      loadUsers();
    }
  }, [isAuthenticated, isLoading, loadUsers]);

  // Debounce search
  useEffect(() => {
    if (searchDebounceRef.current) {
      clearTimeout(searchDebounceRef.current);
    }

    searchDebounceRef.current = setTimeout(() => {
      setDebouncedSearchQuery(searchQuery);
    }, debounceMs);

    return () => {
      if (searchDebounceRef.current) {
        clearTimeout(searchDebounceRef.current);
      }
    };
  }, [searchQuery, debounceMs]);

  // Reset page on filter change
  useEffect(() => {
    setPage(1);
  }, [debouncedSearchQuery, roleFilter, statusFilter]);

  const refresh = useCallback(() => {
    loadUsers(true);
  }, [loadUsers]);

  return {
    // Data
    users,
    stats,

    // Loading states
    loading,
    refreshing,
    error,
    dataFetched,

    // Filters
    searchQuery,
    setSearchQuery,
    debouncedSearchQuery,
    roleFilter,
    setRoleFilter,
    statusFilter,
    setStatusFilter,

    // Pagination
    page,
    setPage,
    pageSize,
    hasMore,

    // Actions
    refresh,
    loadUsers,
  };
}
