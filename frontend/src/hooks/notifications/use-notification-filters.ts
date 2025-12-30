// ===========================================
// useNotificationFilters - Notification filtering hook
// ===========================================

import { useCallback } from "react";
import { useNotifications } from "./use-notifications-core";

/**
 * Hook for managing notification filters.
 */
export const useNotificationFilters = () => {
  const { filters, updateFilters, resetFilters } = useNotifications();

  const setTypeFilter = useCallback(
    (type: string | "all") => {
      updateFilters({ type });
    },
    [updateFilters],
  );

  const setPriorityFilter = useCallback(
    (priority: string | "all") => {
      updateFilters({ priority });
    },
    [updateFilters],
  );

  const setReadFilter = useCallback(
    (readStatus: "all" | "read" | "unread") => {
      updateFilters({ readStatus });
    },
    [updateFilters],
  );

  const setDateFilter = useCallback(
    (dateRange: { start?: Date; end?: Date }) => {
      updateFilters({ dateRange });
    },
    [updateFilters],
  );

  const setSearchFilter = useCallback(
    (search: string) => {
      updateFilters({ search });
    },
    [updateFilters],
  );

  const clearAllFilters = useCallback(() => {
    resetFilters();
  }, [resetFilters]);

  return {
    filters,
    setTypeFilter,
    setPriorityFilter,
    setReadFilter,
    setDateFilter,
    setSearchFilter,
    clearAllFilters,
    resetFilters,
  };
};
