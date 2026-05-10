import { beforeEach, describe, expect, it, vi } from "vitest";

const apiClientMock = {
  get: vi.fn(),
  patch: vi.fn(),
};

vi.mock("@/lib/api-client", () => ({
  apiClient: apiClientMock,
  createDeduplicatedRequest: async <T>(requestFn: () => Promise<T>) => requestFn(),
}));

describe("usersApi settings cache", () => {
  beforeEach(async () => {
    vi.clearAllMocks();

    try {
      const { __clearUsersSettingsCacheForTests } = await import("@/lib/api-endpoints");
      __clearUsersSettingsCacheForTests?.();
    } catch {
      // Cache helper is added by the green step.
    }
  });

  it("reuses fresh settings after the first resolved request", async () => {
    apiClientMock.get.mockResolvedValueOnce({
      data: { theme: "dark", notificationPreferences: { email: { tasks: true } } },
    });

    const { usersApi } = await import("@/lib/api-endpoints");

    await usersApi.getSettings();
    await usersApi.getSettings();

    expect(apiClientMock.get).toHaveBeenCalledTimes(1);
  });

  it("updates cached settings after saving", async () => {
    apiClientMock.get.mockResolvedValueOnce({
      data: { theme: "dark" },
    });
    apiClientMock.patch.mockResolvedValueOnce({
      data: { theme: "light" },
    });

    const { usersApi } = await import("@/lib/api-endpoints");

    await usersApi.getSettings();
    const updated = await usersApi.updateSettings({ theme: "light" });
    const fromCache = await usersApi.getSettings();

    expect(updated).toEqual({ theme: "light" });
    expect(fromCache).toEqual({ theme: "light" });
    expect(apiClientMock.get).toHaveBeenCalledTimes(1);
  });
});
