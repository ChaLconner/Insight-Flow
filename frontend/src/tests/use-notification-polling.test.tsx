import { renderHook, act } from "@testing-library/react";
import { beforeEach, afterEach, describe, expect, it, vi } from "vitest";
import { useNotificationPolling } from "@/hooks/notifications/use-notification-polling";
import { useAuthStore } from "@/stores/auth-store";
import { useNotificationStore } from "@/stores/notification-store";

const { getNotificationsMock, getUnreadCountMock } = vi.hoisted(() => ({
  getNotificationsMock: vi.fn(),
  getUnreadCountMock: vi.fn(),
}));

vi.mock("@/lib/api-endpoints", () => ({
  notificationsApi: {
    getNotifications: getNotificationsMock,
    getUnreadCount: getUnreadCountMock,
  },
}));

describe("useNotificationPolling", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.clearAllMocks();
    getNotificationsMock.mockResolvedValue([]);
    getUnreadCountMock.mockResolvedValue(0);

    act(() => {
      useNotificationStore.getState().clearAllNotifications();
      useNotificationStore.setState({ isLoading: false, unreadCount: 0 });
      useAuthStore.setState({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        isInitialized: false,
        hasVerifiedSession: false,
        lastActivity: 0,
        lastVerified: 0,
      });
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("does not fetch notifications before cached auth is server verified", async () => {
    act(() => {
      useAuthStore.setState({
        user: { id: "user-1", email: "user@example.com" } as never,
        isAuthenticated: true,
        isInitialized: true,
        hasVerifiedSession: false,
      });
    });

    renderHook(() => useNotificationPolling(1000));

    await act(async () => {
      await Promise.resolve();
      vi.advanceTimersByTime(3000);
    });

    expect(getNotificationsMock).not.toHaveBeenCalled();
    expect(getUnreadCountMock).not.toHaveBeenCalled();
  });

  it("starts polling after auth session is server verified", async () => {
    act(() => {
      useAuthStore.setState({
        user: { id: "user-1", email: "user@example.com" } as never,
        isAuthenticated: true,
        isInitialized: true,
        hasVerifiedSession: false,
      });
    });

    const { rerender } = renderHook(() => useNotificationPolling(1000));

    expect(getNotificationsMock).not.toHaveBeenCalled();

    act(() => {
      useAuthStore.setState({ hasVerifiedSession: true });
    });
    rerender();

    await act(async () => {
      await Promise.resolve();
    });

    expect(getNotificationsMock).toHaveBeenCalledTimes(1);
  });
});
