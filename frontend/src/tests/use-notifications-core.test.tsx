import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useNotifications } from "@/hooks/notifications/use-notifications-core";
import { useNotificationStore } from "@/stores/notification-store";
import {
  NotificationPriority,
  NotificationType,
  type Notification,
} from "@/types";

const {
  getNotificationsMock,
  getUnreadCountMock,
  markAsReadMock,
  markAllAsReadMock,
  deleteNotificationMock,
} = vi.hoisted(() => ({
  getNotificationsMock: vi.fn(),
  getUnreadCountMock: vi.fn(),
  markAsReadMock: vi.fn(),
  markAllAsReadMock: vi.fn(),
  deleteNotificationMock: vi.fn(),
}));

vi.mock("@/lib/api-endpoints", () => ({
  notificationsApi: {
    getNotifications: getNotificationsMock,
    getUnreadCount: getUnreadCountMock,
    markAsRead: markAsReadMock,
    markAllAsRead: markAllAsReadMock,
    deleteNotification: deleteNotificationMock,
  },
}));

function notification(
  id: string,
  overrides: Partial<Notification> = {},
): Notification {
  return {
    id,
    userId: "user-1",
    title: `Notification ${id}`,
    message: "Message",
    type: NotificationType.SYSTEM,
    priority: NotificationPriority.MEDIUM,
    read: false,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    ...overrides,
  };
}

describe("useNotifications", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getNotificationsMock.mockResolvedValue([]);
    getUnreadCountMock.mockResolvedValue(0);
    markAsReadMock.mockResolvedValue(undefined);
    markAllAsReadMock.mockResolvedValue([]);
    deleteNotificationMock.mockResolvedValue(undefined);
    useNotificationStore.getState().clearAllNotifications();
    useNotificationStore.setState({
      unreadCount: 0,
      isLoading: false,
      isConnected: false,
      filters: {
        type: "all",
        priority: "all",
        readStatus: "all",
        search: "",
      },
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("fetches notifications and unread count", async () => {
    const items = [notification("one"), notification("two", { read: true })];
    getNotificationsMock.mockResolvedValue(items);
    getUnreadCountMock.mockResolvedValue(1);

    const { result } = renderHook(() => useNotifications());

    await act(async () => {
      await result.current.fetchNotifications();
    });

    expect(getNotificationsMock).toHaveBeenCalledTimes(1);
    expect(getUnreadCountMock).toHaveBeenCalledTimes(1);
    expect(useNotificationStore.getState().notifications).toEqual(items);
    expect(useNotificationStore.getState().unreadCount).toBe(1);
    expect(useNotificationStore.getState().isLoading).toBe(false);
  });

  it("handles unread count changes and unchanged counts", async () => {
    useNotificationStore.setState({ unreadCount: 1 });
    getUnreadCountMock.mockResolvedValueOnce(3).mockResolvedValueOnce(3);
    const { result } = renderHook(() => useNotifications());

    let changed = false;
    await act(async () => {
      changed = await result.current.fetchUnreadCount();
    });
    expect(changed).toBe(true);
    expect(useNotificationStore.getState().unreadCount).toBe(3);

    await act(async () => {
      changed = await result.current.fetchUnreadCount();
    });
    expect(changed).toBe(false);
  });

  it("does not log expected 401 fetch errors", async () => {
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => {});
    getNotificationsMock.mockRejectedValue({ response: { status: 401 } });
    getUnreadCountMock.mockRejectedValue({ response: { status: 401 } });
    const { result } = renderHook(() => useNotifications());

    await act(async () => {
      await result.current.fetchNotifications();
    });
    await expect(result.current.fetchUnreadCount()).resolves.toBe(false);

    expect(consoleError).not.toHaveBeenCalled();
    consoleError.mockRestore();
  });

  it("logs unexpected API errors and keeps optimistic local changes", async () => {
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => {});
    const item = notification("one");
    useNotificationStore.setState({ notifications: [item], unreadCount: 1 });
    markAsReadMock.mockRejectedValue(new Error("mark failed"));
    markAllAsReadMock.mockRejectedValue(new Error("all failed"));
    deleteNotificationMock.mockRejectedValue(new Error("delete failed"));
    const { result } = renderHook(() => useNotifications());

    await act(async () => {
      await result.current.markAsRead("one");
      await result.current.markAllAsRead();
      await result.current.removeNotification("one");
    });

    expect(markAsReadMock).toHaveBeenCalledWith("one");
    expect(markAllAsReadMock).toHaveBeenCalledTimes(1);
    expect(deleteNotificationMock).toHaveBeenCalledWith("one");
    expect(useNotificationStore.getState().notifications).toEqual([]);
    expect(consoleError).toHaveBeenCalledTimes(3);
    consoleError.mockRestore();
  });

  it("creates convenience notifications with expected defaults", () => {
    class MockNotification {
      static readonly permission = "denied";
    }
    vi.stubGlobal("Notification", MockNotification);
    Object.defineProperty(Notification, "permission", {
      configurable: true,
      value: "denied",
    });
    const { result } = renderHook(() => useNotifications());

    act(() => {
      result.current.showSuccess("Saved");
      result.current.showError("Failed", "Try again", { duration: 0 });
      result.current.showWarning("Careful", undefined, {
        priority: NotificationPriority.LOW,
      });
      result.current.showInfo("Heads up", "Message", {
        data: { source: "test" },
      });
    });

    const notifications = useNotificationStore.getState().notifications;
    expect(notifications).toHaveLength(4);
    expect(notifications.map((item) => item.title)).toEqual([
      "Heads up",
      "Careful",
      "Failed",
      "Saved",
    ]);
    expect(notifications[1].priority).toBe(NotificationPriority.LOW);
    expect(notifications[0].data).toEqual({ source: "test" });
  });

  it("marks and removes notifications by type and priority", () => {
    useNotificationStore.setState({
      notifications: [
        notification("low-task", {
          type: NotificationType.TASK_ASSIGNED,
          priority: NotificationPriority.LOW,
        }),
        notification("high-task", {
          type: NotificationType.TASK_ASSIGNED,
          priority: NotificationPriority.HIGH,
        }),
        notification("system", {
          type: NotificationType.SYSTEM,
          priority: NotificationPriority.HIGH,
        }),
      ],
      unreadCount: 3,
    });

    const { result, rerender } = renderHook(() => useNotifications());

    act(() => {
      result.current.markAsReadByType(NotificationType.TASK_ASSIGNED);
    });
    rerender();
    expect(useNotificationStore.getState().unreadCount).toBe(1);

    act(() => {
      result.current.markAsReadByPriority(NotificationPriority.HIGH);
      result.current.removeByType(NotificationType.SYSTEM);
    });
    rerender();
    expect(useNotificationStore.getState().notifications).toHaveLength(2);

    act(() => {
      result.current.removeByPriority(NotificationPriority.LOW);
    });
    expect(useNotificationStore.getState().notifications).toHaveLength(1);
  });

  it("requests notification permission across browser states", async () => {
    const consoleWarn = vi.spyOn(console, "warn").mockImplementation(() => {});
    const { result } = renderHook(() => useNotifications());

    Reflect.deleteProperty(window, "Notification");
    await expect(result.current.requestNotificationPermission()).resolves.toBe(
      false,
    );

    class PermissionNotification {
      static readonly permission = "granted";
    }
    vi.stubGlobal("Notification", PermissionNotification);
    Object.defineProperty(Notification, "permission", {
      configurable: true,
      value: "granted",
    });
    await expect(result.current.requestNotificationPermission()).resolves.toBe(
      true,
    );

    Object.defineProperty(Notification, "permission", {
      configurable: true,
      value: "denied",
    });
    await expect(result.current.requestNotificationPermission()).resolves.toBe(
      false,
    );

    Object.defineProperty(Notification, "permission", {
      configurable: true,
      value: "default",
    });
    Object.defineProperty(Notification, "requestPermission", {
      configurable: true,
      value: vi.fn().mockResolvedValue("granted"),
    });
    await expect(result.current.requestNotificationPermission()).resolves.toBe(
      true,
    );

    expect(consoleWarn).toHaveBeenCalledWith(
      "This browser does not support notifications",
    );
    consoleWarn.mockRestore();
  });

  it("creates browser notifications only when permission is granted", () => {
    const closeMock = vi.fn();
    const notificationMock = vi.fn();
    class BrowserNotification {
      static readonly permission = "denied";
      close = closeMock;

      constructor(title: string, options?: NotificationOptions) {
        notificationMock(title, options);
      }
    }
    vi.stubGlobal("Notification", BrowserNotification);
    Object.defineProperty(Notification, "permission", {
      configurable: true,
      value: "denied",
    });
    const { result } = renderHook(() => useNotifications());

    expect(result.current.showBrowserNotification("Denied")).toBeNull();

    Object.defineProperty(Notification, "permission", {
      configurable: true,
      value: "granted",
    });
    const created = result.current.showBrowserNotification("Granted", {
      body: "Body",
      tag: "tag-1",
      requireInteraction: true,
    });

    expect(created).toBeTruthy();
    expect(notificationMock).toHaveBeenCalledWith("Granted", {
      body: "Body",
      icon: "/favicon.ico",
      tag: "tag-1",
      requireInteraction: true,
    });
  });
});
