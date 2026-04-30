// ===========================================
// useTheme Hook
// ===========================================

import { useEffect, useCallback, useMemo } from "react";
import { usePathname } from "next/navigation";
import {
  useThemeStore,
  themeSelectors,
  themeActions,
} from "@/stores/theme-store";

// Primary theme hook for managing dark/light mode
export const useTheme = () => {
  // SSR detection
  const isSSR = typeof window === "undefined";

  // Check if on auth pages - theme changes should be skipped
  const pathname = usePathname();
  const isAuthPage = pathname?.startsWith("/auth");

  // Zustand store state
  const store = useThemeStore();

  // Selectors
  const currentTheme = themeSelectors.getCurrentTheme(store);
  const isDarkMode = themeSelectors.isDark(store);
  const isLightMode = themeSelectors.isLight(store);
  const isSystemMode = themeSelectors.isSystemMode(store);
  // const _resolvedTheme = themeSelectors.getResolvedTheme(store);
  const systemPrefersDark = themeSelectors.systemPrefersDark(store);
  const availableThemes = themeSelectors.availableThemes(store);
  const colorScheme = themeSelectors.colorScheme(store);
  const nextTheme = themeSelectors.nextTheme(store);

  // SSR-safe system theme detection (only if not already set from store)
  const _systemPrefersDarkValue =
    !isSSR && window.matchMedia("(prefers-color-scheme: dark)").matches;
  const _isAutoTheme = isSystemMode;

  // Actions
  const setTheme = store.setTheme;
  const toggleTheme = store.toggleTheme;
  const setSystemTheme = store.setSystemTheme;
  const enableAutoTheme = store.enableAutoTheme;
  const disableAutoTheme = store.disableAutoTheme;
  const setPrimaryColor = store.setPrimaryColor;
  const resetTheme = store.resetTheme;
  const updateSystemPreference = store.updateSystemPreference;
  const _setSystemPrefersDark = store.setSystemPrefersDark;

  // Listen to system theme changes when using system preference
  useEffect(() => {
    if (!isSystemMode || typeof window === "undefined") {
      return;
    }

    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");

    const handleChange = (e: MediaQueryListEvent) => {
      updateSystemPreference(e.matches);
    };

    mediaQuery.addEventListener("change", handleChange);

    return () => {
      mediaQuery.removeEventListener("change", handleChange);
    };
  }, [isSystemMode, updateSystemPreference]);

  // Apply theme to document (client-side only)
  useEffect(() => {
    // Skip in SSR
    if (typeof window === "undefined") {
      return;
    }

    // Skip theme changes on auth pages - they force dark theme
    if (isAuthPage) {
      return;
    }

    const root = document.documentElement;

    const updateThemeDOM = () => {
      // Remove existing theme classes
      root.classList.remove("light", "dark", "system");

      // Apply current theme
      if (isSystemMode) {
        root.classList.add("system");
        root.classList.toggle("dark", systemPrefersDark);
      } else {
        root.classList.add(currentTheme);
        root.classList.toggle("dark", isDarkMode);
      }

      // Set data attributes for CSS customization
      root.setAttribute("data-theme", currentTheme);
      root.setAttribute("data-color-scheme", colorScheme);

      // Update color-scheme property for native controls
      root.style.colorScheme = colorScheme;

      // Update meta theme-color for mobile browsers
      const metaThemeColor = document.querySelector('meta[name="theme-color"]');
      if (metaThemeColor) {
        const themeColor = isDarkMode ? "#09090b" : "#ffffff"; // Updated to match actual dark bg
        metaThemeColor.setAttribute("content", themeColor);
      }
    };

    updateThemeDOM();

    // Do NOT manually save to localStorage here.
    // Zustand persist middleware (in theme-store.ts) handles storage synchronization automatically.
    // Manual saving creates a race condition and invalidates the storage structure.

  }, [
    currentTheme,
    isDarkMode,
    isSystemMode,
    systemPrefersDark,
    colorScheme,
    store.primaryColor,
    isAuthPage,
  ]);

  // Computed values
  const themeClasses = useMemo(() => {
    return {
      root: `theme-${currentTheme}`,
      isDark: isDarkMode,
      isLight: isLightMode,
      isSystem: isSystemMode,
      auto: _isAutoTheme,
    };
  }, [currentTheme, isDarkMode, isLightMode, isSystemMode, _isAutoTheme]);

  // Helper functions
  const cycleTheme = useCallback(() => {
    if (isSystemMode) {
      // If currently in system mode, switch to dark
      setTheme("dark");
    } else {
      // Cycle through light -> dark -> system
      switch (currentTheme) {
        case "light":
          setTheme("dark");
          break;
        case "dark":
          setTheme("system");
          break;
        case "system":
          setTheme("light");
          break;
        default:
          setTheme("light");
      }
    }
  }, [isSystemMode, currentTheme, setTheme]);

  const getOppositeTheme = useCallback(() => {
    if (isSystemMode) {
      return systemPrefersDark ? "light" : "dark";
    }
    return isDarkMode ? "light" : "dark";
  }, [isSystemMode, systemPrefersDark, isDarkMode]);

  const switchToOpposite = useCallback(() => {
    const oppositeTheme = getOppositeTheme();
    setTheme(oppositeTheme);
  }, [getOppositeTheme, setTheme]);

  // Accessibility helpers
  const prefersReducedMotion = useMemo(() => {
    if (typeof window === "undefined") {
      return false;
    }
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }, []);

  const getContrastText = useCallback((backgroundColor: string) => {
    // Simple contrast calculation (0-255 for each RGB component)
    const rgb = backgroundColor.match(/\d+/g);
    if (!rgb) {
      return "text-white";
    }

    const [r, g, b] = rgb.map(Number);
    const brightness = (r * 299 + g * 587 + b * 114) / 1000;

    return brightness > 128 ? "text-black" : "text-white";
  }, []);

  // Theme variants for different use cases
  const getThemeVariant = useCallback(
    (variant: "glass" | "solid" | "gradient") => {
      const baseClasses = {
        glass:
          "backdrop-blur-md bg-white/10 dark:bg-black/10 border border-white/20 dark:border-white/10",
        solid:
          "bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700",
        gradient:
          "bg-gradient-to-br from-white/20 to-white/5 dark:from-gray-900/20 dark:to-gray-900/5",
      };

      return baseClasses[variant];
    },
    [],
  );

  return {
    // Current state
    currentTheme,
    isDarkMode,
    isLightMode,
    isSystemMode,
    isAutoTheme: _isAutoTheme,
    systemPrefersDark,
    colorScheme,
    nextTheme,
    availableThemes,

    // Theme management
    setTheme,
    toggleTheme,
    cycleTheme,
    switchToOpposite,

    // System theme management
    setSystemTheme,
    enableAutoTheme,
    disableAutoTheme,

    // Color customization
    primaryColor: store.primaryColor,
    setPrimaryColor,

    // Utility actions
    resetTheme,
    updateSystemPreference,

    initializeTheme: themeActions.init,

    // Computed values
    themeClasses,
    getThemeVariant,
    getOppositeTheme,
    getContrastText,

    // Accessibility
    prefersReducedMotion,

    // Storage

    // Store methods for advanced usage
    setSystemPrefersDark: store.setSystemPrefersDark,
  };
};

// ===========================================
// useDarkMode - Simplified dark mode hook
// ===========================================

export const useDarkMode = () => {
  const { isDarkMode, setTheme, toggleTheme, cycleTheme } = useTheme();

  const enableDark = useCallback(() => {
    setTheme("dark");
  }, [setTheme]);

  const enableLight = useCallback(() => {
    setTheme("light");
  }, [setTheme]);

  return {
    isDarkMode,
    enableDark,
    enableLight,
    toggleDarkMode: toggleTheme,
    cycleDarkMode: cycleTheme,
  };
};

// ===========================================
// useSystemTheme - System theme detection hook
// ===========================================

export const useSystemTheme = () => {
  const {
    systemPrefersDark,
    isSystemMode,
    setSystemTheme,
    enableAutoTheme,
    disableAutoTheme,
  } = useTheme();

  const enableSystemTheme = useCallback(() => {
    enableAutoTheme();
  }, [enableAutoTheme]);

  return {
    systemPrefersDark,
    isSystemMode,
    enableSystemTheme,
    disableSystemTheme: disableAutoTheme,
    setSystemTheme,
  };
};

// ===========================================
// useThemeColors - Theme-aware color utilities
// ===========================================

export const useThemeColors = () => {
  const { currentTheme, isDarkMode, primaryColor } = useTheme();

  const colors = useMemo(() => {
    // Define theme-aware color palette
    const baseColors = {
      background: isDarkMode ? "#0f172a" : "#ffffff",
      foreground: isDarkMode ? "#f8fafc" : "#0f172a",
      card: isDarkMode ? "#1e293b" : "#ffffff",
      cardForeground: isDarkMode ? "#f8fafc" : "#0f172a",
      popover: isDarkMode ? "#1e293b" : "#ffffff",
      popoverForeground: isDarkMode ? "#f8fafc" : "#0f172a",
      primary: primaryColor,
      primaryForeground: isDarkMode ? "#ffffff" : "#0f172a",
      secondary: isDarkMode ? "#334155" : "#f1f5f9",
      secondaryForeground: isDarkMode ? "#f8fafc" : "#0f172a",
      muted: isDarkMode ? "#334155" : "#f1f5f9",
      mutedForeground: isDarkMode ? "#94a3b8" : "#64748b",
      accent: isDarkMode ? "#334155" : "#f1f5f9",
      accentForeground: isDarkMode ? "#f8fafc" : "#0f172a",
      destructive: "#ef4444",
      destructiveForeground: "#ffffff",
      border: isDarkMode ? "#334155" : "#e2e8f0",
      input: isDarkMode ? "#334155" : "#e2e8f0",
      ring: primaryColor,
      success: "#10b981",
      warning: "#f59e0b",
      info: "#3b82f6",
      error: "#ef4444",
    };

    return baseColors;
  }, [isDarkMode, primaryColor]);

  const getColor = useCallback(
    (colorKey: keyof typeof colors) => {
      return colors[colorKey];
    },
    [colors],
  );

  const getContrastColor = useCallback((backgroundColor: string) => {
    const rgb = backgroundColor.match(/\d+/g);
    if (!rgb) {
      return "#ffffff";
    }

    const [r, g, b] = rgb.map(Number);
    const brightness = (r * 299 + g * 587 + b * 114) / 1000;

    return brightness > 128 ? "#000000" : "#ffffff";
  }, []);

  const rgba = useCallback((color: string, alpha: number) => {
    const rgb = color.match(/\d+/g);
    if (!rgb) {
      return `rgba(0, 0, 0, ${alpha})`;
    }

    return `rgba(${rgb[0]}, ${rgb[1]}, ${rgb[2]}, ${alpha})`;
  }, []);

  const withOpacity = useCallback(
    (color: string, opacity: number) => {
      return rgba(color, opacity);
    },
    [rgba],
  );

  return {
    colors,
    getColor,
    getContrastColor,
    rgba,
    withOpacity,
    currentTheme,
    isDarkMode,
    primaryColor,
  };
};

// ===========================================
// useThemeAnimation - Animation utilities for theme transitions
// ===========================================

export const useThemeAnimation = () => {
  const { prefersReducedMotion } = useTheme();

  const getTransitionDuration = useCallback(() => {
    return prefersReducedMotion ? 0 : 300;
  }, [prefersReducedMotion]);

  const getTransitionClasses = useCallback(() => {
    if (prefersReducedMotion) {
      return "";
    }
    return "transition-colors duration-300 ease-in-out";
  }, [prefersReducedMotion]);

  const createSlideAnimation = useCallback(
    (direction: "left" | "right" | "up" | "down") => {
      if (prefersReducedMotion) {
        return "";
      }

      const animations = {
        left: "transform translate-x-full opacity-0",
        right: "transform -translate-x-full opacity-0",
        up: "transform translate-y-full opacity-0",
        down: "transform -translate-y-full opacity-0",
      };

      const animationsTarget = {
        left: "transform translate-x-0 opacity-100",
        right: "transform translate-x-0 opacity-100",
        up: "transform translate-y-0 opacity-100",
        down: "transform translate-y-0 opacity-100",
      };

      return {
        initial: animations[direction],
        target: animationsTarget[direction],
        transition:
          "transform duration-300 ease-in-out, opacity duration-300 ease-in-out",
      };
    },
    [prefersReducedMotion],
  );

  return {
    getTransitionDuration,
    getTransitionClasses,
    createSlideAnimation,
    prefersReducedMotion,
  };
};
