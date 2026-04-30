// ===========================================
// Zustand Notification Store
// ===========================================

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Notification } from "@/types";

// Re-export selectors from separate file
export { notificationSelectors } from "./notification-selectors";
// Note: notificationActions is exported separately to avoid circular dependency

// Use the type from types/index.ts directly to ensure consistency
export type CustomNotification = Notification;

export interface NotificationFilters {
  type: string | "all";
  priority: string | "all";
  readStatus: "all" | "read" | "unread";
  search: string;
  dateRange?: { start?: Date; end?: Date };
}

export interface NotificationState {
  // State
  notifications: CustomNotification[];
  unreadCount: number;
  isPermissionGranted: boolean;
  pushEnabled: boolean;
  soundEnabled: boolean;
  vibrationEnabled: boolean;
  isLoading: boolean;
  isConnected: boolean;
  filters: NotificationFilters;

  // Core Actions
  addNotification: (notification: Omit<CustomNotification, "id" | "createdAt" | "updatedAt">) => void;
  setNotifications: (notifications: CustomNotification[]) => void;
  setUnreadCount: (count: number) => void;
  markAsRead: (id: string) => void;
  markAllAsRead: () => void;
  removeNotification: (id: string) => void;
  clearAllNotifications: () => void;
  updateNotification: (id: string, updates: Partial<CustomNotification>) => void;

  // Settings Actions
  setPermissionGranted: (granted: boolean) => void;
  setPushEnabled: (enabled: boolean) => void;
  setSoundEnabled: (enabled: boolean) => void;
  setVibrationEnabled: (enabled: boolean) => void;

  // Loading and Connection
  setLoading: (loading: boolean) => void;
  setConnectionStatus: (connected: boolean) => void;

  // Filter Actions
  updateFilters: (filters: Partial<NotificationState["filters"]>) => void;
  resetFilters: () => void;

  // Real-time Actions
  connect: () => void;
  disconnect: () => void;
  reconnect: () => void;

  // Utility Actions
  getNotificationsByType: (type: string) => CustomNotification[];
  getUnreadNotifications: () => CustomNotification[];
  getRecentNotifications: (limit?: number) => CustomNotification[];
  hasNotification: (id: string) => boolean;
  clearReadNotifications: () => void;
  clearNotifications: () => void;

  // Private methods
  showBrowserNotification: (notification: CustomNotification) => void;
  playNotificationSound: () => void;
}

export const useNotificationStore = create<NotificationState>()(
  persist(
    (set, get) => ({
      // Initial state
      notifications: [],
      unreadCount: 0,
      isPermissionGranted: false,
      pushEnabled: false,
      soundEnabled: true,
      vibrationEnabled: true,
      isLoading: false,
      isConnected: false,
      filters: {
        type: "all",
        priority: "all",
        readStatus: "all",
        search: "",
        dateRange: undefined,
      },

      // Core Actions
      addNotification: (notificationData) => {
        const id = `notification-${Date.now()}-${Math.random().toString(36).substring(2, 11)}`;
        const now = new Date().toISOString();

        const notification: CustomNotification = {
          ...notificationData,
          id,
          createdAt: now,
          updatedAt: now,
        };

        set((state) => ({
          notifications: [notification, ...state.notifications].slice(0, 100),
          unreadCount: notificationData.read ? state.unreadCount : state.unreadCount + 1,
        }));

        get().showBrowserNotification(notification);

        if (get().soundEnabled) {
          get().playNotificationSound();
        }

        if (get().vibrationEnabled && typeof navigator !== "undefined" && navigator.vibrate) {
          navigator.vibrate([200, 100, 200]);
        }
      },

      setNotifications: (notifications) => {
        set({ notifications });
      },

      setUnreadCount: (count) => {
        set({ unreadCount: count });
      },

      markAsRead: (id) => {
        set((state) => {
          const notification = state.notifications.find((n) => n.id === id);
          if (!notification || notification.read) {return state;}

          return {
            notifications: state.notifications.map((n) =>
              n.id === id ? { ...n, read: true, updatedAt: new Date().toISOString() } : n,
            ),
            unreadCount: Math.max(0, state.unreadCount - 1),
          };
        });
      },

      markAllAsRead: () => {
        set((state) => ({
          notifications: state.notifications.map((n) => ({
            ...n,
            read: true,
            updatedAt: new Date().toISOString(),
          })),
          unreadCount: 0,
        }));
      },

      removeNotification: (id) => {
        set((state) => {
          const notification = state.notifications.find((n) => n.id === id);
          const wasUnread = notification && !notification.read;

          return {
            notifications: state.notifications.filter((n) => n.id !== id),
            unreadCount: wasUnread ? Math.max(0, state.unreadCount - 1) : state.unreadCount,
          };
        });
      },

      clearAllNotifications: () => {
        set({ notifications: [], unreadCount: 0 });
      },

      updateNotification: (id, updates) => {
        set((state) => ({
          notifications: state.notifications.map((n) =>
            n.id === id ? { ...n, ...updates, updatedAt: new Date().toISOString() } : n,
          ),
        }));
      },

      // Settings Actions
      setPermissionGranted: (granted) => set({ isPermissionGranted: granted }),
      setPushEnabled: (enabled) => set({ pushEnabled: enabled }),
      setSoundEnabled: (enabled) => set({ soundEnabled: enabled }),
      setVibrationEnabled: (enabled) => set({ vibrationEnabled: enabled }),

      // Loading and Connection
      setLoading: (loading) => set({ isLoading: loading }),
      setConnectionStatus: (connected) => set({ isConnected: connected }),

      // Filter Actions
      updateFilters: (newFilters) => {
        set((state) => ({ filters: { ...state.filters, ...newFilters } }));
      },

      resetFilters: () => {
        set({
          filters: {
            type: "all",
            priority: "all",
            readStatus: "all",
            search: "",
            dateRange: undefined,
          },
        });
      },

      // Real-time Actions
      connect: () => set({ isConnected: true }),
      disconnect: () => set({ isConnected: false }),
      reconnect: () => {
        get().disconnect();
        setTimeout(() => get().connect(), 1000);
      },

      // Utility Actions
      getNotificationsByType: (type) => get().notifications.filter((n) => n.type === type),
      getUnreadNotifications: () => get().notifications.filter((n) => !n.read),
      getRecentNotifications: (limit = 10) => get().notifications.slice(0, limit),
      hasNotification: (id) => get().notifications.some((n) => n.id === id),
      clearReadNotifications: () => {
        set((state) => ({
          notifications: state.notifications.filter((n) => !n.read),
        }));
      },
      clearNotifications: () => get().clearAllNotifications(),

      // Private methods
      showBrowserNotification: (notification: CustomNotification) => {
        if (!get().isPermissionGranted || !get().pushEnabled) {return;}

        if (typeof window !== "undefined" && "Notification" in window) {
          const browserNotification = new Notification(notification.title, {
            body: notification.message,
            icon: "/favicon.ico",
            badge: "/favicon.ico",
            tag: notification.id,
            requireInteraction: notification.priority === "urgent",
          });

          browserNotification.onclick = () => {
            window.focus();
            if (notification.actionUrl) {
              window.location.href = notification.actionUrl;
            }
            get().markAsRead(notification.id);
            browserNotification.close();
          };

          if (notification.priority !== "urgent") {
            setTimeout(() => browserNotification.close(), 5000);
          }
        }
      },

      playNotificationSound: () => {
        if (typeof window !== "undefined") {
          if (process.env.NODE_ENV === "test") {
            return;
          }

          try {
            const audio = new Audio("/sounds/notification.mp3");
            audio.volume = 0.5;
            const playResult = audio.play();
            if (playResult && typeof playResult.catch === "function") {
              playResult.catch((error) => {
                console.error("Could not play notification sound:", error);
              });
            }
          } catch (error) {
            console.error("Notification sound not available:", error);
          }
        }
      },
    }),
    {
      name: "insight-flow-notifications",
      partialize: (state) => ({
        notifications: state.notifications.slice(0, 50),
        soundEnabled: state.soundEnabled,
        vibrationEnabled: state.vibrationEnabled,
        pushEnabled: state.pushEnabled,
      }),
    },
  ),
);
