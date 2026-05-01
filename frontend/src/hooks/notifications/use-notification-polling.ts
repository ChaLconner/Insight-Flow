// ===========================================
// useNotificationPolling - Polling hook
// ===========================================

import { useEffect, useRef, useCallback } from "react";
import { useNotifications } from "./use-notifications-core";
import { useAuthStore } from "@/stores/auth-store";

/**
 * Hook for polling notifications at regular intervals.
 * Automatically pauses when tab is hidden for performance.
 * Uses refs to prevent unnecessary re-fetching and flickering.
 * Only fetches when user is authenticated to prevent 401 errors.
 */
export const useNotificationPolling = (intervalMs = 30000) => {
  const { fetchNotifications, fetchUnreadCount } = useNotifications();
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const isInitialized = useAuthStore((state) => state.isInitialized);
  const hasVerifiedSession = useAuthStore((state) => state.hasVerifiedSession);
  
  // Use refs to store stable function references
  const fetchNotificationsRef = useRef(fetchNotifications);
  const fetchUnreadCountRef = useRef(fetchUnreadCount);
  const hasFetchedRef = useRef(false);
  const notificationsInFlightRef = useRef(false);
  const unreadCountInFlightRef = useRef(false);
  
  // Update refs when functions change
  useEffect(() => {
    fetchNotificationsRef.current = fetchNotifications;
    fetchUnreadCountRef.current = fetchUnreadCount;
  }, [fetchNotifications, fetchUnreadCount]);

  // Stable fetch function that won't cause re-renders
  const stableFetch = useCallback(async () => {
    if (notificationsInFlightRef.current) {
      return;
    }

    notificationsInFlightRef.current = true;
    try {
      await fetchNotificationsRef.current();
    } finally {
      notificationsInFlightRef.current = false;
    }
  }, []);

  const stableFetchUnreadCount = useCallback(async () => {
    if (unreadCountInFlightRef.current) {
      return false;
    }

    unreadCountInFlightRef.current = true;
    try {
      return await fetchUnreadCountRef.current();
    } finally {
      unreadCountInFlightRef.current = false;
    }
  }, []);

  useEffect(() => {
    // Don't fetch until the cached session has been verified with the backend.
    if (!isAuthenticated || !isInitialized || !hasVerifiedSession) {
      return;
    }

    // Only do initial fetch once per authenticated session
    if (!hasFetchedRef.current) {
      hasFetchedRef.current = true;
      void stableFetch();
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
          await stableFetch();
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
        void stableFetch(); // Fetch immediately on resume
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
  }, [
    intervalMs,
    stableFetch,
    stableFetchUnreadCount,
    isAuthenticated,
    isInitialized,
    hasVerifiedSession,
  ]);

  // Reset hasFetchedRef when user logs out
  useEffect(() => {
    if (!isAuthenticated) {
      hasFetchedRef.current = false;
    }
  }, [isAuthenticated]);
};

