// ===========================================
// useNotificationPolling - Polling hook
// ===========================================

import { useEffect, useRef, useCallback } from "react";
import { useNotifications } from "./use-notifications-core";

/**
 * Hook for polling notifications at regular intervals.
 * Automatically pauses when tab is hidden for performance.
 * Uses refs to prevent unnecessary re-fetching and flickering.
 */
export const useNotificationPolling = (intervalMs = 30000) => {
  const { fetchNotifications, fetchUnreadCount } = useNotifications();
  
  // Use refs to store stable function references
  const fetchNotificationsRef = useRef(fetchNotifications);
  const fetchUnreadCountRef = useRef(fetchUnreadCount);
  const hasFetchedRef = useRef(false);
  
  // Update refs when functions change
  useEffect(() => {
    fetchNotificationsRef.current = fetchNotifications;
    fetchUnreadCountRef.current = fetchUnreadCount;
  }, [fetchNotifications, fetchUnreadCount]);

  // Stable fetch function that won't cause re-renders
  const stableFetch = useCallback(async () => {
    await fetchNotificationsRef.current();
  }, []);

  const stableFetchUnreadCount = useCallback(async () => {
    return await fetchUnreadCountRef.current();
  }, []);

  useEffect(() => {
    // Only do initial fetch once
    if (!hasFetchedRef.current) {
      hasFetchedRef.current = true;
      stableFetch();
    }

    let intervalId: ReturnType<typeof setInterval> | null = null;

    const startPolling = () => {
      if (intervalId) {
        return;
      }
      
      intervalId = setInterval(async () => {
        // Don't poll if document is hidden (background tab optimization)
        if (document.visibilityState === "hidden") {
          return;
        }

        const hasChanged = await stableFetchUnreadCount();
        if (hasChanged) {
          stableFetch();
        }
      }, intervalMs);
    };

    const stopPolling = () => {
      if (intervalId) {
        clearInterval(intervalId);
        intervalId = null;
      }
    };

    // Handle visibility change to suspend/resume polling
    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        stableFetch(); // Fetch immediately on resume
        startPolling();
      } else {
        stopPolling();
      }
    };

    // Start initial polling
    startPolling();

    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      stopPolling();
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [intervalMs, stableFetch, stableFetchUnreadCount]);
};

