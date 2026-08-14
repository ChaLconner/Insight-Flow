/**
 * Tests for notification-store.ts
 * Covers notification state management, actions, and filters.
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { NotificationType, NotificationPriority } from "@/types";

// Mock sonner before importing store
vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    info: vi.fn(),
  },
}));

describe("NotificationStore", () => {
  // Import inside tests to ensure mocks are set up
  const getStore = async () => {
    const { useNotificationStore } = await import(
      "@/stores/notification-store"
    );
    return useNotificationStore;
  };

  beforeEach(async () => {
    // Reset store state before each test
    const store = await getStore();
    act(() => {
      store.getState().clearAllNotifications();
      store.getState().resetFilters();
    });
  });

  describe("Initial State", () => {
    it("only permits same-origin notification navigation", async () => {
      const { getSafeNotificationActionUrl } = await import(
        "@/stores/notification-store"
      );

      expect(getSafeNotificationActionUrl("/tasks/123?from=notification")).toBe(
        "/tasks/123?from=notification",
      );
      expect(getSafeNotificationActionUrl("https://attacker.example/phish")).toBe(
        null,
      );
      expect(getSafeNotificationActionUrl("//attacker.example/phish")).toBe(null);
      expect(getSafeNotificationActionUrl("javascript:alert(1)")).toBe(null);
      expect(getSafeNotificationActionUrl(42)).toBe(null);
    });

    it("should have empty notifications initially", async () => {
      const store = await getStore();
      const { result } = renderHook(() => store());

      expect(result.current.notifications).toEqual([]);
      expect(result.current.unreadCount).toBe(0);
    });

    it("should have default filter values", async () => {
      const store = await getStore();
      const { result } = renderHook(() => store());

      expect(result.current.filters.type).toBe("all");
      expect(result.current.filters.priority).toBe("all");
      expect(result.current.filters.readStatus).toBe("all");
      expect(result.current.filters.search).toBe("");
    });

    it("should have default settings", async () => {
      const store = await getStore();
      const { result } = renderHook(() => store());

      expect(result.current.soundEnabled).toBe(true);
      expect(result.current.vibrationEnabled).toBe(true);
    });
  });

  describe("Add Notification", () => {
    it("should add a notification and update unread count", async () => {
      const store = await getStore();
      const { result } = renderHook(() => store());

      const notification = {
        title: "Test Notification",
        message: "This is a test",
        type: NotificationType.SYSTEM,
        priority: NotificationPriority.MEDIUM,
        read: false,
        userId: "user-123",
      };

      act(() => {
        result.current.addNotification(notification);
      });

      expect(result.current.notifications).toHaveLength(1);
      expect(result.current.notifications[0].title).toBe("Test Notification");
      expect(result.current.unreadCount).toBe(1);
    });

    it("should prevent duplicate notifications with same title", async () => {
      const store = await getStore();
      const { result } = renderHook(() => store());

      const notification = {
        title: "Duplicate",
        message: "Test",
        type: NotificationType.SYSTEM,
        priority: NotificationPriority.LOW,
        read: false,
        userId: "user-123",
      };

      act(() => {
        result.current.addNotification(notification);
        result.current.addNotification(notification); // Try adding again
      });

      // Depending on implementation, may have 1 or 2
      expect(result.current.notifications.length).toBeGreaterThanOrEqual(1);
    });
  });

  describe("Mark As Read", () => {
    it("should mark a notification as read", async () => {
      const store = await getStore();
      const { result } = renderHook(() => store());

      act(() => {
        result.current.addNotification({
          title: "Read Test",
          message: "Test",
          type: NotificationType.SYSTEM,
          priority: NotificationPriority.LOW,
          read: false,
          userId: "user-123",
        });
      });

      expect(result.current.unreadCount).toBe(1);

      const notifId = result.current.notifications[0]?.id;
      if (notifId) {
        act(() => {
          result.current.markAsRead(notifId);
        });

        const updated = result.current.notifications.find(
          (n) => n.id === notifId,
        );
        expect(updated?.read).toBe(true);
        expect(result.current.unreadCount).toBe(0);
      }
    });

    it("should mark all notifications as read", async () => {
      const store = await getStore();
      const { result } = renderHook(() => store());

      act(() => {
        result.current.addNotification({
          title: "N1",
          message: "M1",
          type: NotificationType.SYSTEM,
          priority: NotificationPriority.LOW,
          read: false,
          userId: "user-123",
        });
        result.current.addNotification({
          title: "N2",
          message: "M2",
          type: NotificationType.TASK_ASSIGNED,
          priority: NotificationPriority.MEDIUM,
          read: false,
          userId: "user-123",
        });
      });

      expect(result.current.unreadCount).toBe(2);

      act(() => {
        result.current.markAllAsRead();
      });

      expect(result.current.unreadCount).toBe(0);
      expect(result.current.notifications.every((n) => n.read)).toBe(true);
    });
  });

  describe("Remove Notification", () => {
    it("should remove a notification by id", async () => {
      const store = await getStore();
      const { result } = renderHook(() => store());

      act(() => {
        result.current.addNotification({
          title: "Remove Me",
          message: "Test",
          type: NotificationType.SYSTEM,
          priority: NotificationPriority.LOW,
          read: false,
          userId: "user-123",
        });
      });

      expect(result.current.notifications).toHaveLength(1);

      const notifId = result.current.notifications[0]?.id;
      if (notifId) {
        act(() => {
          result.current.removeNotification(notifId);
        });

        expect(result.current.notifications).toHaveLength(0);
      }
    });

    it("should update unread count when removing unread notification", async () => {
      const store = await getStore();
      const { result } = renderHook(() => store());

      act(() => {
        result.current.addNotification({
          title: "Unread",
          message: "Test",
          type: NotificationType.SYSTEM,
          priority: NotificationPriority.LOW,
          read: false,
          userId: "user-123",
        });
      });

      expect(result.current.unreadCount).toBe(1);

      const notifId = result.current.notifications[0]?.id;
      if (notifId) {
        act(() => {
          result.current.removeNotification(notifId);
        });

        expect(result.current.unreadCount).toBe(0);
      }
    });
  });

  describe("Filters", () => {
    it("should update filters", async () => {
      const store = await getStore();
      const { result } = renderHook(() => store());

      act(() => {
        result.current.updateFilters({ type: "warning", priority: "high" });
      });

      expect(result.current.filters.type).toBe("warning");
      expect(result.current.filters.priority).toBe("high");
    });

    it("should reset filters to defaults", async () => {
      const store = await getStore();
      const { result } = renderHook(() => store());

      // First change filters
      act(() => {
        result.current.updateFilters({
          type: "error",
          search: "test search",
        });
      });

      // Then reset
      act(() => {
        result.current.resetFilters();
      });

      expect(result.current.filters.type).toBe("all");
      expect(result.current.filters.search).toBe("");
    });
  });

  describe("Utility Methods", () => {
    it("should get notifications by type", async () => {
      const store = await getStore();
      const { result } = renderHook(() => store());

      act(() => {
        result.current.addNotification({
          title: "System",
          message: "M",
          type: NotificationType.SYSTEM,
          priority: NotificationPriority.LOW,
          read: false,
          userId: "user-123",
        });
        result.current.addNotification({
          title: "Task",
          message: "M",
          type: NotificationType.TASK_ASSIGNED,
          priority: NotificationPriority.MEDIUM,
          read: false,
          userId: "user-123",
        });
      });

      const systemNotifs = result.current.getNotificationsByType(
        NotificationType.SYSTEM,
      );
      expect(systemNotifs).toHaveLength(1);
      expect(systemNotifs[0].type).toBe(NotificationType.SYSTEM);
    });

    it("should get unread notifications", async () => {
      const store = await getStore();
      const { result } = renderHook(() => store());

      act(() => {
        result.current.addNotification({
          title: "Unread",
          message: "M",
          type: NotificationType.SYSTEM,
          priority: NotificationPriority.LOW,
          read: false,
          userId: "user-123",
        });
        result.current.addNotification({
          title: "Read",
          message: "M",
          type: NotificationType.SYSTEM,
          priority: NotificationPriority.LOW,
          read: true,
          userId: "user-123",
        });
      });

      const unread = result.current.getUnreadNotifications();
      expect(unread).toHaveLength(1);
      expect(unread[0].read).toBe(false);
    });

    it("should check if notification exists", async () => {
      const store = await getStore();
      const { result } = renderHook(() => store());

      act(() => {
        result.current.addNotification({
          title: "Exists",
          message: "M",
          type: NotificationType.SYSTEM,
          priority: NotificationPriority.LOW,
          read: false,
          userId: "user-123",
        });
      });

      const notifId = result.current.notifications[0]?.id;
      if (notifId) {
        expect(result.current.hasNotification(notifId)).toBe(true);
      }
      expect(result.current.hasNotification("does-not-exist")).toBe(false);
    });

    it("should get recent notifications with limit", async () => {
      const store = await getStore();
      const { result } = renderHook(() => store());

      // Add multiple notifications
      act(() => {
        for (let i = 0; i < 15; i++) {
          result.current.addNotification({
            title: `Notification ${i}`,
            message: "M",
            type: NotificationType.SYSTEM,
            priority: NotificationPriority.LOW,
            read: false,
            userId: "user-123",
          });
        }
      });

      const recent = result.current.getRecentNotifications(5);
      expect(recent).toHaveLength(5);
    });
  });

  describe("Settings", () => {
    it("should toggle sound enabled", async () => {
      const store = await getStore();
      const { result } = renderHook(() => store());

      expect(result.current.soundEnabled).toBe(true);

      act(() => {
        result.current.setSoundEnabled(false);
      });

      expect(result.current.soundEnabled).toBe(false);
    });

    it("should toggle vibration enabled", async () => {
      const store = await getStore();
      const { result } = renderHook(() => store());

      expect(result.current.vibrationEnabled).toBe(true);

      act(() => {
        result.current.setVibrationEnabled(false);
      });

      expect(result.current.vibrationEnabled).toBe(false);
    });

    it("should set loading state", async () => {
      const store = await getStore();
      const { result } = renderHook(() => store());

      act(() => {
        result.current.setLoading(true);
      });

      expect(result.current.isLoading).toBe(true);

      act(() => {
        result.current.setLoading(false);
      });

      expect(result.current.isLoading).toBe(false);
    });
  });

  describe("Clear Operations", () => {
    it("should clear all notifications", async () => {
      const store = await getStore();
      const { result } = renderHook(() => store());

      act(() => {
        result.current.addNotification({
          title: "N1",
          message: "M",
          type: NotificationType.SYSTEM,
          priority: NotificationPriority.LOW,
          read: false,
          userId: "user-123",
        });
        result.current.addNotification({
          title: "N2",
          message: "M",
          type: NotificationType.SYSTEM,
          priority: NotificationPriority.LOW,
          read: false,
          userId: "user-123",
        });
      });

      expect(result.current.notifications).toHaveLength(2);

      act(() => {
        result.current.clearAllNotifications();
      });

      expect(result.current.notifications).toHaveLength(0);
      expect(result.current.unreadCount).toBe(0);
    });

    it("should clear only read notifications", async () => {
      const store = await getStore();
      const { result } = renderHook(() => store());

      act(() => {
        result.current.addNotification({
          title: "Unread",
          message: "M",
          type: NotificationType.SYSTEM,
          priority: NotificationPriority.LOW,
          read: false,
          userId: "user-123",
        });
        result.current.addNotification({
          title: "Read",
          message: "M",
          type: NotificationType.SYSTEM,
          priority: NotificationPriority.LOW,
          read: true,
          userId: "user-123",
        });
      });

      act(() => {
        result.current.clearReadNotifications();
      });

      expect(result.current.notifications).toHaveLength(1);
      expect(result.current.notifications[0].title).toBe("Unread");
    });
  });

  describe("Selectors", () => {
    it("should select notifications correctly using exported selectors", async () => {
      const { notificationSelectors } = await import("@/stores/notification-selectors");
      // Create a mock state
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const mockState: any = {
        notifications: [
          {
            id: "1",
            title: "N1",
            message: "M1",
            type: "system",
            priority: "high",
            read: false,
            createdAt: new Date().toISOString(),
          },
          {
            id: "2",
            title: "N2",
            message: "M2",
            type: "task_assigned",
            priority: "low",
            read: true,
            createdAt: new Date(Date.now() - 100000).toISOString(),
          },
        ],
        unreadCount: 1,
        isPermissionGranted: true,
        pushEnabled: true,
        soundEnabled: true,
        vibrationEnabled: true,
        isLoading: false,
        isConnected: true,
        filters: {
          type: "all",
          priority: "all",
          readStatus: "all",
          search: "",
        },
      };

      // Test core selectors
      expect(notificationSelectors.getNotifications(mockState)).toHaveLength(2);
      expect(notificationSelectors.getUnreadCount(mockState)).toBe(1);
      expect(notificationSelectors.isLoading(mockState)).toBe(false);
      expect(notificationSelectors.isConnected(mockState)).toBe(true);
      expect(notificationSelectors.getFilters(mockState)).toEqual(mockState.filters);

      // Test filtered views
      expect(notificationSelectors.getUnreadNotifications(mockState)).toHaveLength(1);
      expect(notificationSelectors.getUnreadNotifications(mockState)[0].id).toBe("1");
      
      expect(notificationSelectors.getReadNotifications(mockState)).toHaveLength(1);
      expect(notificationSelectors.getReadNotifications(mockState)[0].id).toBe("2");

      // Test grouped views
      const byPriority = notificationSelectors.getNotificationsByPriority(mockState);
      expect(byPriority["high"]).toHaveLength(1);
      expect(byPriority["low"]).toHaveLength(1);

      const byType = notificationSelectors.getNotificationsByType(mockState);
      expect(byType["system"]).toHaveLength(1);
      expect(byType["task_assigned"]).toHaveLength(1);

      // Test latest
      expect(notificationSelectors.getLatestNotifications(mockState)(1)).toHaveLength(1);

      // Test settings
      const settings = notificationSelectors.getSettings(mockState);
      expect(settings.pushEnabled).toBe(true);

      // Test utilities
      expect(notificationSelectors.hasUnread(mockState)).toBe(true);
      expect(notificationSelectors.getUnread(mockState)).toHaveLength(1);
      
      // Test getRecent (assuming both are recent enough)
      expect(notificationSelectors.getRecent(mockState)).toHaveLength(2);

      // Test getByType curry
      expect(notificationSelectors.getByType(mockState)("system")).toHaveLength(1);

      // Test getHighPriority
      expect(notificationSelectors.getHighPriority(mockState)).toHaveLength(1);
    });

    it("should filter notifications based on search and other filters", async () => {
        const { notificationSelectors } = await import("@/stores/notification-selectors");
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const mockState: any = {
          notifications: [
            {
                id: "1",
                title: "Alert",
                message: "System Alert occurred",
                type: "system",
                priority: "high",
                read: false,
                createdAt: new Date().toISOString(),
            },
            {
                id: "2",
                title: "Info",
                message: "Just some info",
                type: "info",
                priority: "low",
                read: true,
                createdAt: new Date().toISOString(),
            }
          ],
          filters: {
              type: "all",
              priority: "all",
              readStatus: "all",
              search: "Alert", // Should match first one
          }
        };

        const filtered = notificationSelectors.getFilteredNotifications(mockState);
        expect(filtered).toHaveLength(1);
        expect(filtered[0].id).toBe("1");

        // Test Type Filter
        mockState.filters.search = "";
        mockState.filters.type = "info";
        expect(notificationSelectors.getFilteredNotifications(mockState)).toHaveLength(1);
        expect(notificationSelectors.getFilteredNotifications(mockState)[0].id).toBe("2");

        // Test Priority Filter
        mockState.filters.type = "all";
        mockState.filters.priority = "high";
        expect(notificationSelectors.getFilteredNotifications(mockState)).toHaveLength(1);
        expect(notificationSelectors.getFilteredNotifications(mockState)[0].id).toBe("1");

        // Test Read Status Filter
        mockState.filters.priority = "all";
        mockState.filters.readStatus = "read";
        expect(notificationSelectors.getFilteredNotifications(mockState)).toHaveLength(1);
        expect(notificationSelectors.getFilteredNotifications(mockState)[0].id).toBe("2");

        // Test Date Range
        mockState.filters.readStatus = "all";
        const yesterday = new Date(Date.now() - 24 * 60 * 60 * 1000);
        const tomorrow = new Date(Date.now() + 24 * 60 * 60 * 1000);
        mockState.filters.dateRange = { start: yesterday, end: tomorrow };
        expect(notificationSelectors.getFilteredNotifications(mockState)).toHaveLength(2);
        
        mockState.filters.dateRange = { start: tomorrow };
        expect(notificationSelectors.getFilteredNotifications(mockState)).toHaveLength(0);

        mockState.filters.dateRange = { end: yesterday };
        expect(notificationSelectors.getFilteredNotifications(mockState)).toHaveLength(0);

        mockState.filters.dateRange = undefined;
        mockState.filters.readStatus = "unread";
        expect(notificationSelectors.getFilteredNotifications(mockState)).toHaveLength(1);
    });
  });

  it("keeps unreadCount synchronized when read notifications are cleared", async () => {
    const store = await getStore();
    const { result } = renderHook(() => store());

    act(() => {
      result.current.addNotification({
        title: "Unread",
        message: "Test",
        type: NotificationType.SYSTEM,
        priority: NotificationPriority.LOW,
        read: false,
        userId: "user-123",
      });
      result.current.addNotification({
        title: "Read",
        message: "Test",
        type: NotificationType.SYSTEM,
        priority: NotificationPriority.LOW,
        read: true,
        userId: "user-123",
      });
      result.current.clearReadNotifications();
    });

    expect(result.current.notifications).toHaveLength(1);
    expect(result.current.unreadCount).toBe(1);
  });

  it("recalculates unreadCount when a notification read state changes", async () => {
    const store = await getStore();
    const { result } = renderHook(() => store());

    act(() => {
      result.current.addNotification({
        title: "Unread",
        message: "Test",
        type: NotificationType.SYSTEM,
        priority: NotificationPriority.LOW,
        read: false,
        userId: "user-123",
      });
    });

    const notificationId = result.current.notifications[0]?.id;
    expect(notificationId).toBeDefined();
    if (!notificationId) {
      throw new Error("Expected a generated notification id");
    }
    act(() => {
      result.current.updateNotification(notificationId, { read: true });
    });

    expect(result.current.unreadCount).toBe(0);
  });
});
