// ===========================================
// useUnreadNotifications - Simplified unread notifications hook
// ===========================================

import { useCallback } from "react";
import { useNotifications } from "./use-notifications-core";

/**
 * Simplified hook for managing unread notifications only.
 */
export const useUnreadNotifications = () => {
  const { unreadNotifications, unreadCount, markAsRead, markAllAsRead } = useNotifications();

  const markAsReadById = useCallback(
    (id: string) => {
      markAsRead(id);
    },
    [markAsRead],
  );

  return {
    unreadNotifications,
    unreadCount,
    markAsRead: markAsReadById,
    markAllAsRead,
  };
};
