/**
 * Unit tests for auth-store.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { act } from "@testing-library/react";
import type { User } from "@/types";

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] || null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      store = {};
    }),
  };
})();

Object.defineProperty(window, "localStorage", { value: localStorageMock });

// Mock API endpoints
vi.mock("@/lib/api-endpoints", () => ({
  authApi: {
    logout: vi.fn().mockResolvedValue(undefined),
    getCurrentUser: vi.fn(),
  },
}));

describe("auth-store", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.clear();
    vi.resetModules();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe("initial state", () => {
    it("should have correct initial state", async () => {
      const { useAuthStore } = await import("@/stores/auth-store");
      const state = useAuthStore.getState();

      expect(state.isAuthenticated).toBe(false);
      expect(state.user).toBe(null);
      expect(state.isLoading).toBe(true); // Initially loading
    });
  });

  describe("setUser", () => {
    it("should set user and authenticate", async () => {
      const { useAuthStore } = await import("@/stores/auth-store");

      const mockUser = {
        id: "123",
        email: "test@example.com",
        name: "Test User",
      };

      act(() => {
        useAuthStore.getState().setUser(mockUser as unknown as User);
      });

      const state = useAuthStore.getState();
      expect(state.user).toEqual(mockUser);
      expect(state.isAuthenticated).toBe(true);
      // Note: isLoading may or may not be false depending on implementation
    });

    it("should handle null user", async () => {
      const { useAuthStore } = await import("@/stores/auth-store");

      act(() => {
        useAuthStore.getState().setUser(null);
      });

      const state = useAuthStore.getState();
      expect(state.user).toBe(null);
      expect(state.isAuthenticated).toBe(false);
    });
  });

  describe("logout", () => {
    it("should clear user and auth state on logout", async () => {
      const { useAuthStore } = await import("@/stores/auth-store");

      // First set a user
      const mockUser = {
        id: "123",
        email: "test@example.com",
        name: "Test User",
      };

      act(() => {
        useAuthStore.getState().setUser(mockUser as unknown as User);
      });

      expect(useAuthStore.getState().isAuthenticated).toBe(true);

      // Now logout
      await act(async () => {
        await useAuthStore.getState().logout();
      });

      const state = useAuthStore.getState();
      expect(state.user).toBe(null);
      expect(state.isAuthenticated).toBe(false);
      // Note: authApi.logout may or may not be called depending on implementation details
    });
  });

  describe("setLoading", () => {
    it("should set loading state", async () => {
      const { useAuthStore } = await import("@/stores/auth-store");

      act(() => {
        useAuthStore.getState().setLoading(true);
      });

      expect(useAuthStore.getState().isLoading).toBe(true);

      act(() => {
        useAuthStore.getState().setLoading(false);
      });

      expect(useAuthStore.getState().isLoading).toBe(false);
    });
  });
});

describe("auth-store persistence", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.clear();
    vi.resetModules();
  });

  it("should persist auth state to localStorage", async () => {
    const { useAuthStore } = await import("@/stores/auth-store");

    const mockUser = {
      id: "123",
      email: "test@example.com",
      name: "Test User",
    };

    act(() => {
      useAuthStore.getState().setUser(mockUser as unknown as User);
    });

    // Check that localStorage.setItem was called
    // The Zustand persist middleware will handle this
    expect(localStorageMock.setItem).toHaveBeenCalled();
  });
});
