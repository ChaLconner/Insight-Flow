import { beforeEach, describe, expect, it, vi } from "vitest";
import { UserRole } from "@/types";

const loginMock = vi.fn();
const logoutMock = vi.fn();
const setLoadingMock = vi.fn();
const initializeAuthMock = vi.fn();
const setLoggingOutMock = vi.fn();
const clearDeduplicatedRequestsMock = vi.fn();
const clearQueryCacheMock = vi.fn();
const clearTokensMock = vi.fn();
const clearServiceWorkerCacheMock = vi.fn();

const toastMock = {
  success: vi.fn(),
  info: vi.fn(),
};

const apiClientMock = {
  post: vi.fn(),
};

vi.mock("@/stores/auth-store", () => ({
  useAuthStore: {
    getState: () => ({
      login: loginMock,
      logout: logoutMock,
      setLoading: setLoadingMock,
      initializeAuth: initializeAuthMock,
    }),
  },
}));

vi.mock("sonner", () => ({
  toast: toastMock,
}));

vi.mock("@/lib/api-client", () => ({
  apiClient: apiClientMock,
  setLoggingOut: setLoggingOutMock,
  clearDeduplicatedRequests: clearDeduplicatedRequestsMock,
}));

vi.mock("@/providers/query-provider", () => ({
  clearQueryCache: clearQueryCacheMock,
}));

vi.mock("@/utils/token-manager", () => ({
  TokenManager: {
    clearTokens: clearTokensMock,
  },
}));

vi.mock("@/components/providers/service-worker-registration", () => ({
  clearServiceWorkerCache: clearServiceWorkerCacheMock,
}));

describe("auth actions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("logs in successfully and emits the auth event", async () => {
    const dispatchEventSpy = vi.spyOn(window, "dispatchEvent");
    const { authActions } = await import("@/stores/auth-actions");

    await authActions.loginSuccess(
      {
        accessToken: "token",
        refreshToken: "refresh",
        expiresAt: "2026-01-01T00:00:00Z",
        user: {
          id: "user-1",
          email: "jane@example.com",
          username: "janedoe",
          firstName: "Jane",
          name: "Jane Doe",
          role: UserRole.MEMBER,
          isActive: true,
          emailVerified: true,
          createdAt: "2026-01-01T00:00:00Z",
          updatedAt: "2026-01-01T00:00:00Z",
        },
      },
      { rememberMe: true },
    );

    expect(clearDeduplicatedRequestsMock).toHaveBeenCalled();
    expect(clearQueryCacheMock).toHaveBeenCalled();
    expect(clearTokensMock).toHaveBeenCalled();
    expect(loginMock).toHaveBeenCalledWith(
      expect.objectContaining({ id: "user-1" }),
      { rememberMe: true },
    );
    expect(dispatchEventSpy).toHaveBeenCalled();
    expect(toastMock.success).toHaveBeenCalledWith("Welcome back, Jane Doe!", {
      description: "You have successfully logged in.",
    });
  });

  it("rejects a login response without a user profile", async () => {
    const { authActions } = await import("@/stores/auth-actions");

    await expect(authActions.loginSuccess({ message: "Login successful" })).rejects.toThrow(
      "Authentication response did not include a user profile",
    );
    expect(loginMock).not.toHaveBeenCalled();
    expect(clearDeduplicatedRequestsMock).not.toHaveBeenCalled();
  });

  it("logs out through the server and clears local state", async () => {
    const dispatchEventSpy = vi.spyOn(window, "dispatchEvent");
    apiClientMock.post.mockResolvedValueOnce({ data: {} });

    const { authActions } = await import("@/stores/auth-actions");
    await authActions.logout();

    expect(setLoadingMock).toHaveBeenCalledWith(true);
    expect(apiClientMock.post).toHaveBeenCalledWith("/auth/logout");
    expect(setLoggingOutMock).toHaveBeenCalledWith(true);
    expect(clearServiceWorkerCacheMock).toHaveBeenCalled();
    expect(logoutMock).toHaveBeenCalled();
    expect(dispatchEventSpy).toHaveBeenCalled();
    expect(toastMock.info).toHaveBeenCalledWith("Logged out", {
      description: "You have been safely logged out.",
    });
  });

  it("still flips logging-out state when server logout fails", async () => {
    apiClientMock.post.mockRejectedValueOnce(new Error("network down"));

    const { authActions } = await import("@/stores/auth-actions");
    await authActions.logout();

    expect(setLoggingOutMock).toHaveBeenCalledWith(true);
    expect(logoutMock).toHaveBeenCalled();
  });

  it("initializes auth and reports initialization failures", async () => {
    const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    const { authActions } = await import("@/stores/auth-actions");

    await authActions.initializeAuth();
    expect(initializeAuthMock).toHaveBeenCalled();

    initializeAuthMock.mockRejectedValueOnce(new Error("init failed"));
    await authActions.initializeAuth();

    expect(consoleErrorSpy).toHaveBeenCalledWith(
      "Auth initialization failed:",
      expect.any(Error),
    );

    consoleErrorSpy.mockRestore();
  });
});
