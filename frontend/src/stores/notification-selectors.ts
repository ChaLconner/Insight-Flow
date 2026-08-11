// ===========================================
// Notification Store Selectors
// ===========================================

import type { CustomNotification, NotificationState } from "./notification-store";

const matchesNotificationDateRange = (
  notification: CustomNotification,
  dateRange: NotificationState["filters"]["dateRange"],
): boolean => {
  if (!dateRange) {
    return true;
  }

  const notificationDate = new Date(notification.createdAt);
  if (dateRange.start) {
    if (notificationDate < dateRange.start) {
      return false;
    }
  }
  if (dateRange.end) {
    if (notificationDate > dateRange.end) {
      return false;
    }
  }
  return true;
};

const matchesNotificationType = (
  notification: CustomNotification,
  type: NotificationState["filters"]["type"],
): boolean => {
  if (type === "all") {
    return true;
  }
  return notification.type === type;
};

const matchesNotificationPriority = (
  notification: CustomNotification,
  priority: NotificationState["filters"]["priority"],
): boolean => {
  if (priority === "all") {
    return true;
  }
  return notification.priority === priority;
};

const matchesNotificationReadStatus = (
  notification: CustomNotification,
  readStatus: NotificationState["filters"]["readStatus"],
): boolean => {
  if (readStatus === "read") {
    return notification.read;
  }
  if (readStatus === "unread") {
    return !notification.read;
  }
  return true;
};

const matchesNotificationSearch = (
  notification: CustomNotification,
  search: string,
): boolean => {
  if (!search) {
    return true;
  }
  return notification.message.toLowerCase().includes(search.toLowerCase());
};

const matchesNotificationFilters = (
  notification: CustomNotification,
  filters: NotificationState["filters"],
): boolean => {
  return [
    matchesNotificationType(notification, filters.type),
    matchesNotificationPriority(notification, filters.priority),
    matchesNotificationReadStatus(notification, filters.readStatus),
    matchesNotificationSearch(notification, filters.search),
    matchesNotificationDateRange(notification, filters.dateRange),
  ].every(Boolean);
};

export const notificationSelectors = {
  // Core selectors
  getNotifications: (state: NotificationState) => state.notifications,
  getAllNotifications: (state: NotificationState) => state.notifications,
  getUnreadCount: (state: NotificationState) => state.unreadCount,

  // Compatibility selectors
  isLoading: (state: NotificationState) => state.isLoading,
  isConnected: (state: NotificationState) => state.isConnected,
  getFilters: (state: NotificationState) => state.filters,

  // Filtered views
  getUnreadNotifications: (state: NotificationState) =>
    state.notifications.filter((n) => !n.read),
  getReadNotifications: (state: NotificationState) =>
    state.notifications.filter((n) => n.read),

  getFilteredNotifications: (state: NotificationState) =>
    state.notifications.filter((notification) =>
      matchesNotificationFilters(notification, state.filters),
    ),

  // Grouped views
  getNotificationsByPriority: (state: NotificationState) => {
    const grouped = {} as Record<string, CustomNotification[]>;
    state.notifications.forEach((notification) => {
      if (!grouped[notification.priority]) {
        grouped[notification.priority] = [];
      }
      grouped[notification.priority].push(notification);
    });
    return grouped;
  },

  getNotificationsByType: (state: NotificationState) => {
    const grouped = {} as Record<string, CustomNotification[]>;
    state.notifications.forEach((notification) => {
      if (!grouped[notification.type]) {
        grouped[notification.type] = [];
      }
      grouped[notification.type].push(notification);
    });
    return grouped;
  },

  // Latest notifications
  getLatestNotifications:
    (state: NotificationState) =>
    (limit = 10) =>
      state.notifications.slice(0, limit) as CustomNotification[],

  // Settings
  getSettings: (state: NotificationState) => ({
    isPermissionGranted: state.isPermissionGranted,
    pushEnabled: state.pushEnabled,
    soundEnabled: state.soundEnabled,
    vibrationEnabled: state.vibrationEnabled,
  }),

  // Utility selectors
  hasUnread: (state: NotificationState) => state.unreadCount > 0,
  getUnread: (state: NotificationState) =>
    state.notifications.filter((n) => !n.read) as CustomNotification[],

  getRecent: (state: NotificationState) => {
    const twentyFourHoursAgo = new Date(Date.now() - 24 * 60 * 60 * 1000);
    return state.notifications.filter(
      (n) => new Date(n.createdAt) > twentyFourHoursAgo,
    );
  },

  getByType: (state: NotificationState) => (type: string) =>
    state.notifications.filter((n) => n.type === type),

  getHighPriority: (state: NotificationState) =>
    state.notifications.filter(
      (n) => n.priority === "urgent" || n.priority === "high",
    ),
} as const;
