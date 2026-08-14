"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import type { User, UserRole } from "@/types";
import { useAuthStore } from "@/stores/auth-store";
import { usersApi } from "@/lib/api-endpoints";
import { toast } from "sonner";
import { getErrorMessage } from "@/lib/error-utils";
import type { UserStatsData } from "../types";
import { DEFAULT_USER_STATS } from "../types";

type RoleFilter = UserRole | "all";
type UserStatusFilter = "all" | "active" | "inactive";

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
  roleFilter: RoleFilter;
  setRoleFilter: (role: RoleFilter) => void;
  statusFilter: UserStatusFilter;
  setStatusFilter: (status: UserStatusFilter) => void;

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
  const filterKey = [debouncedSearchQuery, roleFilter, statusFilter].join("|");

  // Pagination state
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);

  // Refs
  const searchDebounceRef = useRef<NodeJS.Timeout | null>(null);
  const loadedQueryKeyRef = useRef<string | null>(null);
  const previousFilterKeyRef = useRef(filterKey);
  const activeRequestIdRef = useRef(0);
  const usersRequestControllerRef = useRef<AbortController | null>(null);

  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const userId = useAuthStore((state) => state.user?.id ?? null);
  const isLoading = useAuthStore((state) => state.isLoading);

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

      const queryKey = [
        userId,
        page,
        pageSize,
        debouncedSearchQuery,
        roleFilter,
        statusFilter,
      ].join("|");

      // The effect depends on loadUsers, whose dataFetched dependency changes
      // after the first response. Skip re-running the same query deterministically
      // instead of relying on a timing window.
      if (!forceRefresh && loadedQueryKeyRef.current === queryKey) {
        return;
      }

      const requestId = activeRequestIdRef.current + 1;
      activeRequestIdRef.current = requestId;
      usersRequestControllerRef.current?.abort();
      const controller = new AbortController();
      usersRequestControllerRef.current = controller;

      try {
        if (forceRefresh) {
          setRefreshing(true);
          if (!dataFetched) {
            setLoading(true);
          }
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
              controller.signal,
            ),
            forceRefresh || !dataFetched ? fetchStats() : Promise.resolve(),
          ]);

          if (requestId !== activeRequestIdRef.current || controller.signal.aborted) {
            return;
          }

          const userList = Array.isArray(usersData)
            ? usersData
            : ((usersData as Record<string, unknown>).data as User[]) ?? [];
          setUsers(userList);
          setHasMore(userList.length === pageSize);
          loadedQueryKeyRef.current = queryKey;
        } catch (apiError) {
          if (requestId !== activeRequestIdRef.current || controller.signal.aborted) {
            return;
          }
          console.error("API issue:", apiError);
          // Preserve the last successful list during refreshes. A failed
          // request is not a successful empty result and must remain retryable.
          loadedQueryKeyRef.current = null;
          setError("Failed to load users");
          toast.error("Failed to load users", {
            description: getErrorMessage(apiError),
          });
          return;
        }

        setDataFetched(true);
      } catch (err) {
        if (requestId !== activeRequestIdRef.current || controller.signal.aborted) {
          return;
        }
        console.error("Error loading users:", err);
        setError("Failed to load users");
        toast.error("Failed to load users", {
          description: getErrorMessage(err),
        });
      } finally {
        if (requestId === activeRequestIdRef.current) {
          setLoading(false);
          setRefreshing(false);
          if (usersRequestControllerRef.current === controller) {
            usersRequestControllerRef.current = null;
          }
        }
      }
    },
    [
      isAuthenticated,
      userId,
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

    if (!isAuthenticated) {
      activeRequestIdRef.current += 1;
      usersRequestControllerRef.current?.abort();
      usersRequestControllerRef.current = null;
      loadedQueryKeyRef.current = null;
      previousFilterKeyRef.current = filterKey;
      setUsers([]);
      setStats(DEFAULT_USER_STATS);
      setHasMore(false);
      setDataFetched(false);
      setError(null);
      setLoading(false);
      setRefreshing(false);
      setPage(1);
      return;
    }

    if (previousFilterKeyRef.current !== filterKey) {
      previousFilterKeyRef.current = filterKey;
      if (page !== 1) {
        setPage(1);
        return;
      }
    }

    void loadUsers();
  }, [filterKey, isAuthenticated, isLoading, loadUsers, page]);

  useEffect(() => {
    return () => {
      activeRequestIdRef.current += 1;
      usersRequestControllerRef.current?.abort();
      usersRequestControllerRef.current = null;
    };
  }, []);

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
