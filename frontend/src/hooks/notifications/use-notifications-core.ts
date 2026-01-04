// ===========================================
// useNotifications Core Hook
// ===========================================

import { useEffect, useCallback, useMemo } from "react";
import {
  useNotificationStore,
  notificationSelectors,
} from "@/stores/notification-store";
import { NotificationType, NotificationPriority, type Notification } from "@/types";
import { notificationsApi } from "@/lib/api-endpoints";

/**
 * Primary notifications hook for managing in-app notifications.
 * Provides access to notification state, CRUD operations, and API integration.
 */
export const useNotifications = () => {
  // Zustand store state
  const store = useNotificationStore();

  // Selectors
  const notifications = notificationSelectors.getAllNotifications(store);
  const unreadCount = notificationSelectors.getUnreadCount(store);
  const isLoading = notificationSelectors.isLoading(store);
  const isConnected = notificationSelectors.isConnected(store);
  const filters = notificationSelectors.getFilters(store);
  const unreadNotifications = notificationSelectors.getUnreadNotifications(store);
  const readNotifications = notificationSelectors.getReadNotifications(store);
  const filteredNotifications = notificationSelectors.getFilteredNotifications(store);
  const notificationsByPriority = notificationSelectors.getNotificationsByPriority(store);
  const notificationsByType = notificationSelectors.getNotificationsByType(store);
  const latestNotifications = notificationSelectors.getLatestNotifications(store);

  // Actions
  const {
    addNotification,
    setNotifications,
    setUnreadCount,
    markAsRead,
    markAllAsRead,
    removeNotification,
    clearNotifications,
    clearReadNotifications,
    updateFilters,
    resetFilters,
    setLoading,
    setConnectionStatus,
    connect,
    disconnect,
    reconnect,
  } = store;

  // API Integration
  const fetchNotifications = useCallback(async () => {
    try {
      setLoading(true);
      const data = await notificationsApi.getNotifications();
      setNotifications(data);
      const count = await notificationsApi.getUnreadCount();
      setUnreadCount(count);
    } catch (error: unknown) {
      // Silently ignore 401 errors - they're expected when user isn't authenticated
      const axiosError = error as { response?: { status?: number } };
      if (axiosError?.response?.status !== 401) {
        console.error("Failed to fetch notifications", error);
      }
    } finally {
      setLoading(false);
    }
  }, [setNotifications, setUnreadCount, setLoading]);

  const fetchUnreadCount = useCallback(async () => {
    try {
      const count = await notificationsApi.getUnreadCount();
      if (count !== unreadCount) {
        setUnreadCount(count);
        return true;
      }
      return false;
    } catch (error: unknown) {
      // Silently ignore 401 errors - they're expected when user isn't authenticated
      const axiosError = error as { response?: { status?: number } };
      if (axiosError?.response?.status !== 401) {
        console.error("Failed to fetch unread count", error);
      }
      return false;
    }
  }, [unreadCount, setUnreadCount]);

  const markAsReadApi = useCallback(
    async (id: string) => {
      try {
        markAsRead(id);
        await notificationsApi.markAsRead(id);
      } catch (error) {
        console.error("Failed to mark as read API", error);
      }
    },
    [markAsRead],
  );

  const markAllAsReadApi = useCallback(async () => {
    try {
      markAllAsRead();
      await notificationsApi.markAllAsRead();
    } catch (error) {
      console.error("Failed to mark all as read API", error);
    }
  }, [markAllAsRead]);

  const deleteNotificationApi = useCallback(
    async (id: string) => {
      try {
        removeNotification(id);
        await notificationsApi.deleteNotification(id);
      } catch (error) {
        console.error("Failed to delete notification API", error);
      }
    },
    [removeNotification],
  );

  // Browser notification integration
  const showToastForNotification = useCallback((notification: Notification) => {
    if (typeof window !== "undefined") {
      try {
        if ("Notification" in window && Notification.permission === "granted") {
          new Notification(notification.title, {
            body: notification.message,
            icon: "/favicon.ico",
          });
        }
      } catch (error) {
        console.warn("Could not show notification:", error);
      }
    }
  }, []);

  // Create notification helper
  const createNotification = useCallback(
    (
      title: string,
      message: string,
      options: {
        type?: string;
        priority?: string;
        duration?: number;
        action?: { label: string; handler: () => void };
        data?: Record<string, unknown>;
        showToast?: boolean;
      } = {},
    ) => {
      const notification: Notification = {
        id: Date.now().toString() + Math.random().toString(36).substring(2, 11),
        userId: "current-user",
        title,
        message,
        type: (options.type as NotificationType) ?? NotificationType.SYSTEM,
        priority: (options.priority as NotificationPriority) ?? NotificationPriority.MEDIUM,
        read: false,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        data: options.data as Record<string, unknown>,
        actionUrl: undefined,
      };

      addNotification(notification);

      if (options.showToast !== false) {
        showToastForNotification(notification);
      }

      return notification.id;
    },
    [addNotification, showToastForNotification],
  );

  // Convenience methods
  const showSuccess = useCallback(
    (title: string, message?: string, options?: { priority?: string; action?: { label: string; handler: () => void }; data?: Record<string, unknown> }) => {
      return createNotification(title, message ?? "", {
        type: NotificationType.SYSTEM,
        priority: options?.priority ?? NotificationPriority.MEDIUM,
        action: options?.action,
        data: options?.data,
      });
    },
    [createNotification],
  );

  const showError = useCallback(
    (title: string, message?: string, options?: { priority?: string; action?: { label: string; handler: () => void }; data?: Record<string, unknown>; duration?: number }) => {
      return createNotification(title, message ?? "", {
        type: NotificationType.SYSTEM,
        priority: options?.priority ?? NotificationPriority.HIGH,
        action: options?.action,
        data: options?.data,
        showToast: options?.duration !== 0,
      });
    },
    [createNotification],
  );

  const showWarning = useCallback(
    (title: string, message?: string, options?: { priority?: string; action?: { label: string; handler: () => void }; data?: Record<string, unknown> }) => {
      return createNotification(title, message ?? "", {
        type: NotificationType.SYSTEM,
        priority: options?.priority ?? NotificationPriority.MEDIUM,
        action: options?.action,
        data: options?.data,
      });
    },
    [createNotification],
  );

  const showInfo = useCallback(
    (title: string, message?: string, options?: { priority?: string; action?: { label: string; handler: () => void }; data?: Record<string, unknown> }) => {
      return createNotification(title, message ?? "", {
        type: NotificationType.SYSTEM,
        priority: options?.priority ?? NotificationPriority.MEDIUM,
        action: options?.action,
        data: options?.data,
      });
    },
    [createNotification],
  );

  // Bulk operations
  const markAsReadByType = useCallback(
    (type: string) => {
      const typeNotifications = notificationsByType[type] || [];
      typeNotifications.forEach((notification: Notification) => {
        if (!notification.read) {
          markAsRead(notification.id);
        }
      });
    },
    [notificationsByType, markAsRead],
  );

  const markAsReadByPriority = useCallback(
    (priority: string) => {
      const priorityNotifications = notificationsByPriority[priority] || [];
      priorityNotifications.forEach((notification: Notification) => {
        if (!notification.read) {
          markAsRead(notification.id);
        }
      });
    },
    [notificationsByPriority, markAsRead],
  );

  const removeByType = useCallback(
    (type: string) => {
      const typeNotifications = notificationsByType[type] || [];
      typeNotifications.forEach((notification: Notification) => {
        removeNotification(notification.id);
      });
    },
    [notificationsByType, removeNotification],
  );

  const removeByPriority = useCallback(
    (priority: string) => {
      const priorityNotifications = notificationsByPriority[priority] || [];
      priorityNotifications.forEach((notification: Notification) => {
        removeNotification(notification.id);
      });
    },
    [notificationsByPriority, removeNotification],
  );

  // Auto-connect effect
  useEffect(() => {
    if (!isConnected && notifications.length > 0) {
      connect();
    }
  }, [isConnected, connect, notifications.length]);

  // Auto-remove old notifications
  useEffect(() => {
    const RETENTION_DAYS = 7;
    const cutoffTime = new Date();
    cutoffTime.setDate(cutoffTime.getDate() - RETENTION_DAYS);

    const currentNotifications = useNotificationStore.getState().notifications;
    const oldNotificationIds = currentNotifications
      .filter((notification: Notification) => new Date(notification.createdAt) < cutoffTime)
      .map((n: Notification) => n.id);

    if (oldNotificationIds.length > 0) {
      const store = useNotificationStore.getState();
      oldNotificationIds.forEach((id: string) => {
        store.removeNotification(id);
      });
    }
  }, [notifications.length]);

  // Statistics
  const notificationStats = useMemo(() => {
    const stats = {
      total: notifications.length,
      unread: unreadCount,
      read: notifications.length - unreadCount,
      byType: {} as Record<string, number>,
      byPriority: {} as Record<string, number>,
    };

    (["system", "task_assigned", "task_status_changed", "task_due_date", "project_invitation", "project_update", "mention", "comment"] as string[]).forEach((type) => {
      stats.byType[type] = notifications.filter((n: Notification) => n.type === type).length;
    });

    (["low", "medium", "high", "urgent"] as string[]).forEach((priority) => {
      stats.byPriority[priority] = notifications.filter((n: Notification) => n.priority === priority).length;
    });

    return stats;
  }, [notifications, unreadCount]);

  // Permission handling
  const requestNotificationPermission = useCallback(async () => {
    if (!("Notification" in window)) {
      console.warn("This browser does not support notifications");
      return false;
    }

    if (Notification.permission === "granted") {return true;}
    if (Notification.permission === "denied") {return false;}

    const permission = await Notification.requestPermission();
    return permission === "granted";
  }, []);

  const showBrowserNotification = useCallback(
    (title: string, options?: { body?: string; icon?: string; tag?: string; requireInteraction?: boolean }) => {
      if (Notification.permission !== "granted") {return null;}

      return new Notification(title, {
        body: options?.body,
        icon: options?.icon ?? "/favicon.ico",
        tag: options?.tag,
        requireInteraction: options?.requireInteraction,
      });
    },
    [],
  );

  return {
    // Core state
    notifications,
    unreadCount,
    isLoading,
    isConnected,
    filters,

    // Filtered views
    unreadNotifications,
    readNotifications,
    filteredNotifications,
    notificationsByPriority,
    notificationsByType,
    latestNotifications,

    // Statistics
    notificationStats,

    // CRUD operations
    createNotification,
    markAsRead: markAsReadApi,
    markAllAsRead: markAllAsReadApi,
    markAsReadByType,
    markAsReadByPriority,
    removeNotification: deleteNotificationApi,
    clearNotifications,
    clearReadNotifications,
    removeByType,
    removeByPriority,

    // API Actions
    fetchNotifications,
    fetchUnreadCount,

    // Convenience methods
    showSuccess,
    showError,
    showWarning,
    showInfo,

    // Filter management
    updateFilters,
    resetFilters,

    // Real-time connection
    connect,
    disconnect,
    reconnect,
    setConnectionStatus,
    setLoading,

    // Browser notifications
    requestNotificationPermission,
    showBrowserNotification,

    // Integration
    showToastForNotification,

    // Store methods for advanced usage
    addNotification: store.addNotification,
  };
};
