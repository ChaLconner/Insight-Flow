// ===========================================
// Notification Store Selectors
// ===========================================

import type { Notification } from "@/types";

// Custom notification type alias
type CustomNotification = Notification;

// Store state interface for selectors
interface NotificationState {
  notifications: CustomNotification[];
  unreadCount: number;
  isPermissionGranted: boolean;
  pushEnabled: boolean;
  soundEnabled: boolean;
  vibrationEnabled: boolean;
  isLoading: boolean;
  isConnected: boolean;
  filters: {
    type: string | "all";
    priority: string | "all";
    readStatus: "all" | "read" | "unread";
    search: string;
    dateRange?: { start?: Date; end?: Date };
  };
}

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

  getFilteredNotifications: (state: NotificationState) => {
    const { filters } = state;
    return state.notifications.filter((notification) => {
      if (filters.type !== "all" && notification.type !== filters.type) {
        return false;
      }
      if (filters.priority !== "all" && notification.priority !== filters.priority) {
        return false;
      }
      if (filters.readStatus === "read" && notification.read) {
        return false;
      }
      if (filters.readStatus === "unread" && !notification.read) {
        return false;
      }
      if (
        filters.search &&
        !notification.message.toLowerCase().includes(filters.search.toLowerCase())
      ) {
        return false;
      }
      if (filters.dateRange) {
        const notificationDate = new Date(notification.createdAt);
        if (filters.dateRange.start && notificationDate < filters.dateRange.start) {
          return false;
        }
        if (filters.dateRange.end && notificationDate > filters.dateRange.end) {
          return false;
        }
      }
      return true;
    });
  },

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
