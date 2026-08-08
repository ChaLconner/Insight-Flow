import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  clearAuthenticatedCaches,
  registerAuthenticatedCacheClearer,
} from "@/lib/auth-cache";

describe("authenticated cache registry", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("clears registered synchronous and asynchronous caches", async () => {
    const syncClearer = vi.fn();
    const asyncClearer = vi.fn().mockResolvedValue(undefined);
    const unregisterSync = registerAuthenticatedCacheClearer(syncClearer);
    const unregisterAsync = registerAuthenticatedCacheClearer(asyncClearer);

    await clearAuthenticatedCaches();

    expect(syncClearer).toHaveBeenCalledOnce();
    expect(asyncClearer).toHaveBeenCalledOnce();

    unregisterSync();
    unregisterAsync();
  });

  it("continues clearing when one cache clearer fails", async () => {
    const warning = vi.spyOn(console, "warn").mockImplementation(() => {});
    const failingClearer = vi.fn().mockRejectedValue(new Error("cache failure"));
    const healthyClearer = vi.fn();
    const unregisterFailing = registerAuthenticatedCacheClearer(failingClearer);
    const unregisterHealthy = registerAuthenticatedCacheClearer(healthyClearer);

    await clearAuthenticatedCaches();

    expect(healthyClearer).toHaveBeenCalledOnce();
    expect(warning).toHaveBeenCalledWith(
      "Failed to clear authenticated cache",
      expect.any(Error),
    );

    unregisterFailing();
    unregisterHealthy();
  });
});
