import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DEFAULT_USER_STATS } from "@/app/users/types";
import { UserRole } from "@/types";

const mocks = vi.hoisted(() => ({
  searchUsers: vi.fn(),
  getStats: vi.fn(),
}));

const authState = vi.hoisted(() => ({
  isAuthenticated: true,
  isLoading: false,
  user: { id: "user-1" },
}));

vi.mock("@/lib/api-endpoints", () => ({
  usersApi: mocks,
}));

vi.mock("@/stores/auth-store", () => ({
  useAuthStore: (selector: (state: typeof authState) => unknown) =>
    selector(authState),
}));

import { useUsers } from "@/app/users/hooks/useUsers";

describe("useUsers performance guards", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.searchUsers.mockResolvedValue([]);
    mocks.getStats.mockResolvedValue(DEFAULT_USER_STATS);
  });

  it("does not repeat the initial query when dataFetched changes the callback", async () => {
    const { result } = renderHook(() => useUsers({ debounceMs: 0 }));

    await waitFor(() => expect(result.current.dataFetched).toBe(true));

    expect(mocks.searchUsers).toHaveBeenCalledTimes(1);
    expect(mocks.getStats).toHaveBeenCalledTimes(1);
  });

  it("keeps failed requests retryable instead of reporting an empty success", async () => {
    mocks.searchUsers.mockRejectedValueOnce(new Error("backend unavailable"));

    const { result } = renderHook(() => useUsers({ debounceMs: 0 }));

    await waitFor(() => expect(result.current.error).toBe("Failed to load users"));

    expect(result.current.dataFetched).toBe(false);
    expect(result.current.users).toEqual([]);

    mocks.searchUsers.mockResolvedValueOnce([{ id: "user-2" }]);
    await act(async () => {
      await result.current.loadUsers(true);
    });

    expect(result.current.error).toBeNull();
    expect(result.current.dataFetched).toBe(true);
    expect(result.current.users).toEqual([{ id: "user-2" }]);
  });

  it("resets pagination before loading a changed filter", async () => {
    const { result } = renderHook(() => useUsers({ debounceMs: 0, pageSize: 10 }));

    await waitFor(() => expect(result.current.dataFetched).toBe(true));

    act(() => {
      result.current.setPage(2);
    });
    await waitFor(() => expect(mocks.searchUsers).toHaveBeenCalledTimes(2));
    expect(mocks.searchUsers.mock.calls.at(-1)?.[1]).toBe(10);

    act(() => {
      result.current.setRoleFilter(UserRole.ADMIN);
    });

    await waitFor(() => {
      expect(result.current.page).toBe(1);
      expect(mocks.searchUsers.mock.calls.at(-1)?.[1]).toBe(0);
    });
  });
});
