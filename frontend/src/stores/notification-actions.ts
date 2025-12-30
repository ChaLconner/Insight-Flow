// ===========================================
// Notification Store Actions
// ===========================================

import type { Notification } from "@/types";
import { NotificationType, NotificationPriority } from "@/types";
import { useNotificationStore } from "./notification-store";

type CustomNotification = Notification;

export const notificationActions = {
  /**
   * Request notification permission from the browser.
   */
  requestPermission: async (): Promise<boolean> => {
    if (typeof window === "undefined" || !("Notification" in window)) {
      return false;
    }

    try {
      const permission = await Notification.requestPermission();
      const granted = permission === "granted";

      useNotificationStore.getState().setPermissionGranted(granted);
      return granted;
    } catch (error) {
      console.error("Failed to request notification permission:", error);
      return false;
    }
  },

  /**
   * Show a test notification for debugging.
   */
  showTestNotification: () => {
    const { addNotification } = useNotificationStore.getState();

    addNotification({
      userId: "test",
      type: NotificationType.SYSTEM,
      title: "Test Notification",
      message: "This is a test notification from Insight Flow",
      data: { test: true },
      read: false,
      priority: NotificationPriority.MEDIUM,
    });
  },

  /**
   * Handle notification click - navigate and mark as read.
   */
  handleNotificationClick: (notification: CustomNotification) => {
    if (notification.actionUrl) {
      window.location.href = notification.actionUrl;
    }

    useNotificationStore.getState().markAsRead(notification.id);
  },

  /**
   * Filter notifications with multiple criteria.
   */
  filterNotifications: (filters: {
    type?: string;
    priority?: string;
    read?: boolean;
    dateRange?: { start: Date; end: Date };
  }) => {
    const { notifications } = useNotificationStore.getState();

    return notifications.filter((notification) => {
      if (filters.type && notification.type !== filters.type) {
        return false;
      }
      if (filters.priority && notification.priority !== filters.priority) {
        return false;
      }
      if (filters.read !== undefined && notification.read !== filters.read) {
        return false;
      }
      if (filters.dateRange) {
        const notificationDate = new Date(notification.createdAt);
        if (
          notificationDate < filters.dateRange.start ||
          notificationDate > filters.dateRange.end
        ) {
          return false;
        }
      }
      return true;
    });
  },

  /**
   * Mark multiple notifications as read.
   */
  markMultipleAsRead: (ids: string[]) => {
    const { markAsRead } = useNotificationStore.getState();
    ids.forEach((id) => markAsRead(id));
  },

  /**
   * Remove multiple notifications.
   */
  removeMultiple: (ids: string[]) => {
    const { removeNotification } = useNotificationStore.getState();
    ids.forEach((id) => removeNotification(id));
  },
};
