import { beforeEach, describe, expect, it, vi } from "vitest";

function installMatchMedia(matches = false) {
  const listeners = new Set<(event: MediaQueryListEvent) => void>();

  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: vi.fn().mockImplementation(() => ({
      matches,
      media: "(prefers-color-scheme: dark)",
      onchange: null,
      addEventListener: vi.fn((_: string, listener: (event: MediaQueryListEvent) => void) => {
        listeners.add(listener);
      }),
      removeEventListener: vi.fn((_: string, listener: (event: MediaQueryListEvent) => void) => {
        listeners.delete(listener);
      }),
      dispatchEvent: vi.fn(),
    })),
  });

  return listeners;
}

describe("theme store actions", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
    vi.useRealTimers();
    window.localStorage.clear();
    document.documentElement.className = "";
    delete document.documentElement.dataset.theme;
    delete document.documentElement.dataset.colorScheme;
    document.documentElement.style.colorScheme = "";
    document.head.innerHTML = '<meta name="theme-color" content="#ffffff">';
    installMatchMedia(false);
  });

  it("applies light theme attributes and selectors", async () => {
    const { themeActions, themeSelectors, useThemeStore } = await import("@/stores/theme-store");

    useThemeStore.getState().setTheme("light");
    const state = useThemeStore.getState();

    expect(state.theme).toBe("light");
    expect(document.documentElement.classList.contains("light")).toBe(true);
    expect(document.documentElement.dataset.theme).toBe("light");
    expect(themeSelectors.isLight(state)).toBe(true);
    expect(themeActions.getThemeLabel("dark")).toBe("Dark");
  });

  it("falls back to the default theme when persisted state is invalid", async () => {
    window.localStorage.setItem("insight-flow-theme", "not-json");
    const consoleWarn = vi.spyOn(console, "warn").mockImplementation(() => {});

    const { useThemeStore } = await import("@/stores/theme-store");

    expect(useThemeStore.getState().theme).toBe("dark");
    expect(consoleWarn).toHaveBeenCalledWith(
      "Failed to parse persisted theme; using the default.",
      expect.any(Error),
    );
    consoleWarn.mockRestore();
  });

  it("initializes system theme, updates system preference, and cleans listener", async () => {
    const listeners = installMatchMedia(true);
    const { useThemeStore } = await import("@/stores/theme-store");

    useThemeStore.getState().setTheme("system");
    useThemeStore.getState().initializeTheme();

    expect(useThemeStore.getState().resolvedTheme).toBe("dark");
    expect(document.documentElement.classList.contains("dark")).toBe(true);
    expect(listeners.size).toBe(1);

    useThemeStore.getState().updateSystemPreference(false);
    expect(useThemeStore.getState().resolvedTheme).toBe("light");

    const cleanup = useThemeStore.getState().listenToSystemTheme();
    cleanup?.();

    expect(listeners.size).toBe(0);
  });

  it("supports auto-theme helpers, meta updates, and reset", async () => {
    const { useThemeStore } = await import("@/stores/theme-store");

    useThemeStore.getState().enableAutoTheme();
    expect(useThemeStore.getState().theme).toBe("system");

    useThemeStore.getState().setPrimaryColor("#ff0000");
    expect(document.documentElement.style.getPropertyValue("--primary-color")).toBe("#ff0000");

    useThemeStore.getState().disableAutoTheme();
    expect(useThemeStore.getState().theme).toBe("light");

    useThemeStore.getState().applyTheme("dark");
    expect(
      document.querySelector('meta[name="theme-color"]')?.getAttribute("content"),
    ).toBe("#0f172a");

    useThemeStore.getState().setTransitioning(true);
    expect(useThemeStore.getState().isTransitioning).toBe(true);

    useThemeStore.getState().resetTheme();
    expect(useThemeStore.getState().theme).toBe("light");
    expect(useThemeStore.getState().nextTheme).toBe("dark");
  });

  it("runs transition helpers and icon helpers", async () => {
    vi.useFakeTimers();
    const { themeActions, useThemeStore, themeTransitionStyles } = await import("@/stores/theme-store");

    themeActions.setThemeWithTransition("dark");
    expect(useThemeStore.getState().isTransitioning).toBe(true);
    expect(document.documentElement.classList.contains("theme-transitioning")).toBe(true);

    vi.advanceTimersByTime(300);
    expect(useThemeStore.getState().isTransitioning).toBe(false);
    expect(document.documentElement.classList.contains("theme-transitioning")).toBe(false);

    themeActions.toggleThemeWithTransition();
    vi.advanceTimersByTime(300);
    expect(useThemeStore.getState().theme).toBe("light");

    useThemeStore.setState({
      ...useThemeStore.getState(),
      theme: "system",
      currentTheme: "system",
      resolvedTheme: "dark",
      isSystem: true,
      isSystemMode: true,
    });

    expect(themeActions.getThemeIcon()).toBe("Sun");
    expect(themeActions.supportsTransitions()).toBe(true);
    expect(themeTransitionStyles).toContain("theme-transitioning");
  });

  it("covers reduced-motion support and direct theme toggling branches", async () => {
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: query.includes("prefers-reduced-motion"),
        media: query,
        onchange: null,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    });

    const { themeActions, useThemeStore } = await import("@/stores/theme-store");

    useThemeStore.getState().toggleTheme();
    expect(useThemeStore.getState().theme).toBe("light");

    useThemeStore.setState({
      ...useThemeStore.getState(),
      theme: "dark",
      currentTheme: "dark",
      resolvedTheme: "dark",
      isSystem: false,
      isSystemMode: false,
    });

    expect(themeActions.getThemeIcon("dark")).toBe("Sun");
    expect(themeActions.supportsTransitions()).toBe(false);
  });
});
