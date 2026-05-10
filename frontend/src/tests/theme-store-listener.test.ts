import { beforeEach, describe, expect, it, vi } from "vitest";

describe("theme store system listener", () => {
  const addEventListener = vi.fn();
  const removeEventListener = vi.fn();

  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();

    window.localStorage.clear();
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: vi.fn().mockImplementation(() => ({
        matches: false,
        media: "(prefers-color-scheme: dark)",
        onchange: null,
        addEventListener,
        removeEventListener,
        dispatchEvent: vi.fn(),
      })),
    });
  });

  it("does not register duplicate system theme listeners", async () => {
    const { useThemeStore } = await import("@/stores/theme-store");

    const firstCleanup = useThemeStore.getState().listenToSystemTheme();
    const secondCleanup = useThemeStore.getState().listenToSystemTheme();

    expect(addEventListener).toHaveBeenCalledTimes(1);

    firstCleanup?.();
    secondCleanup?.();

    expect(removeEventListener).toHaveBeenCalledTimes(1);
  });
});
