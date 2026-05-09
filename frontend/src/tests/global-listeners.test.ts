import { afterEach, describe, expect, it, vi } from "vitest";

describe("global browser listeners", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.doUnmock("@/stores/auth-store");
    vi.resetModules();
  });

  it("registers app visibility cleanup once and can unregister it", async () => {
    vi.resetModules();
    const addSpy = vi.spyOn(document, "addEventListener");
    const removeSpy = vi.spyOn(document, "removeEventListener");

    const {
      registerAppVisibilityCleanup,
      unregisterAppVisibilityCleanup,
    } = await import("@/stores/app-store");

    registerAppVisibilityCleanup();
    registerAppVisibilityCleanup();

    const visibilityAdds = addSpy.mock.calls.filter(
      ([eventName]) => eventName === "visibilitychange",
    );
    expect(visibilityAdds).toHaveLength(1);

    unregisterAppVisibilityCleanup();

    const visibilityRemoves = removeSpy.mock.calls.filter(
      ([eventName]) => eventName === "visibilitychange",
    );
    expect(visibilityRemoves).toHaveLength(1);
  });

  it("clears alerts when document becomes hidden", async () => {
    vi.resetModules();
    const {
      useAppStore,
      unregisterAppVisibilityCleanup,
    } = await import("@/stores/app-store");

    useAppStore.getState().addAlert({
      type: "info",
      title: "Saved",
      message: "Draft saved",
    });

    Object.defineProperty(document, "hidden", {
      configurable: true,
      value: true,
    });
    document.dispatchEvent(new Event("visibilitychange"));

    expect(useAppStore.getState().alerts).toHaveLength(0);
    unregisterAppVisibilityCleanup();
  });

  it("does not install no-op auth event listeners on module import", async () => {
    vi.resetModules();
    vi.doMock("@/stores/auth-store", () => ({
      useAuthStore: {
        getState: vi.fn(() => ({})),
      },
    }));
    const addSpy = vi.spyOn(window, "addEventListener");

    await import("@/stores/auth-actions");

    const authListenerAdds = addSpy.mock.calls.filter(([eventName]) =>
      eventName === "auth:login" || eventName === "auth:logout"
    );
    expect(authListenerAdds).toHaveLength(0);
  });
});

