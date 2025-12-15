// ===========================================
// Zustand Theme Store
// ===========================================

import { create } from "zustand";
import { persist } from "zustand/middleware";

type Theme = "light" | "dark" | "system";

interface ThemeState {
  // State
  theme: Theme;
  currentTheme: Theme; // Alias for theme
  resolvedTheme: "light" | "dark";
  systemPrefersDark: boolean;
  isSystemMode: boolean;
  isSystem: boolean; // Short alias for isSystemMode
  isTransitioning: boolean;
  availableThemes: string[];
  colorScheme: string;
  nextTheme: string;
  primaryColor: string;

  // Actions
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
  setResolvedTheme: (resolvedTheme: "light" | "dark") => void;
  setTransitioning: (transitioning: boolean) => void;

  // System theme actions
  setSystemTheme: (prefersDark: boolean) => void;
  applySystemTheme: () => void;
  enableAutoTheme: () => void;
  disableAutoTheme: () => void;
  updateSystemPreference: (prefersDark: boolean) => void;
  listenToSystemTheme: () => void | (() => void);

  // Color actions
  setPrimaryColor: (color: string) => void;

  // Utility actions
  getTheme: () => Theme;
  getResolvedTheme: () => "light" | "dark";
  initializeTheme: () => void;
  applyTheme: (theme: "light" | "dark") => void;
  resetTheme: () => void;
  updateMetaThemeColor: (theme: "light" | "dark") => void;

  // Advanced utility
  setSystemPrefersDark: (prefersDark: boolean) => void; // For compatibility
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set, get) => ({
      // Initial state
      theme: "system",
      currentTheme: "system", // Alias for theme
      resolvedTheme: "light",
      systemPrefersDark: false,
      isSystemMode: true, // Default to system mode
      isSystem: true, // Default to system mode
      isTransitioning: false,
      availableThemes: ["light", "dark", "system"],
      colorScheme: "light",
      nextTheme: "dark",
      primaryColor: "#3b82f6",

      // Actions
      setTheme: (theme) => {
        set({
          theme,
          currentTheme: theme, // Keep alias in sync
          isSystemMode: theme === "system",
          nextTheme:
            theme === "light" ? "dark" : theme === "dark" ? "system" : "light",
        });

        // Apply theme immediately if not system (client-side only)
        if (typeof window !== "undefined") {
          if (theme !== "system") {
            get().applyTheme(theme);
          } else {
            // For system theme, listen to system changes
            get().listenToSystemTheme();
          }

          // Save to localStorage
          localStorage.setItem("insight-flow-theme", theme);
        }
      },

      toggleTheme: () => {
        const currentTheme = get().theme;
        const newTheme = currentTheme === "light" ? "dark" : "light";
        get().setTheme(newTheme);
      },

      // System theme actions
      setSystemTheme: (prefersDark) => {
        set({
          systemPrefersDark: prefersDark,
          resolvedTheme: prefersDark ? "dark" : "light",
        });
      },

      enableAutoTheme: () => {
        set({
          theme: "system",
          currentTheme: "system",
          isSystemMode: true,
          isSystem: true,
        });

        if (typeof window !== "undefined") {
          get().applySystemTheme();
          localStorage.setItem("insight-flow-theme", "system");
        }
      },

      disableAutoTheme: () => {
        set({
          theme: "light",
          currentTheme: "light",
          isSystemMode: false,
        });

        if (typeof window !== "undefined") {
          get().applyTheme("light");
          localStorage.setItem("insight-flow-theme", "light");
        }
      },

      updateSystemPreference: (prefersDark) => {
        set({
          systemPrefersDark: prefersDark,
          resolvedTheme: prefersDark ? "dark" : "light",
        });

        if (get().isSystemMode && typeof window !== "undefined") {
          get().applyTheme(prefersDark ? "dark" : "light");
        }
      },

      // Color actions
      setPrimaryColor: (color) => {
        set({ primaryColor: color });

        if (typeof window !== "undefined") {
          document.documentElement.style.setProperty("--primary-color", color);
        }
      },

      // Utility actions
      resetTheme: () => {
        set({
          theme: "light",
          currentTheme: "light",
          resolvedTheme: "light",
          systemPrefersDark: false,
          isSystemMode: false,
          isTransitioning: false,
          availableThemes: ["light", "dark", "system"],
          colorScheme: "light",
          nextTheme: "dark",
          primaryColor: "#3b82f6",
        });

        if (typeof window !== "undefined") {
          get().applyTheme("light");
          localStorage.setItem("insight-flow-theme", "light");
        }
      },

      // Advanced utility for compatibility
      setSystemPrefersDark: (prefersDark) => {
        set({ systemPrefersDark: prefersDark });
        get().updateSystemPreference(prefersDark);
      },

      setResolvedTheme: (resolvedTheme) => {
        set({ resolvedTheme });
      },

      setTransitioning: (transitioning) => {
        set({ isTransitioning: transitioning });
      },

      // Utilities
      getTheme: () => {
        return get().theme;
      },

      getResolvedTheme: () => {
        return get().resolvedTheme;
      },

      initializeTheme: () => {
        // Load theme from localStorage or use default (client-side only)
        let savedTheme: Theme | null = null;

        if (typeof window !== "undefined") {
          savedTheme = localStorage.getItem("insight-flow-theme") as Theme;
        }

        const initialTheme = savedTheme || "system";

        set({ theme: initialTheme });

        // Apply initial theme (client-side only)
        if (typeof window !== "undefined") {
          if (initialTheme === "system") {
            get().listenToSystemTheme();
            get().applySystemTheme();
          } else {
            get().applyTheme(initialTheme);
          }
        }
      },

      applyTheme: (theme) => {
        if (typeof window === "undefined") {
          return;
        }

        const root = document.documentElement;

        // Remove existing theme classes
        root.classList.remove("light", "dark");

        // Add new theme class
        root.classList.add(theme);

        // Update resolved theme
        get().setResolvedTheme(theme);

        // Update meta theme-color for mobile browsers
        get().updateMetaThemeColor(theme);

        // Dispatch theme change event
        window.dispatchEvent(
          new CustomEvent("themechange", {
            detail: { theme },
          }),
        );
      },

      applySystemTheme: () => {
        if (typeof window === "undefined") {
          return;
        }

        const systemTheme = window.matchMedia("(prefers-color-scheme: dark)")
          .matches
          ? "dark"
          : "light";

        get().applyTheme(systemTheme);
      },

      listenToSystemTheme: () => {
        if (typeof window === "undefined") {
          return;
        }

        const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");

        const handleChange = () => {
          if (get().theme === "system") {
            get().applySystemTheme();
          }
        };

        // Use the modern addEventListener API
        mediaQuery.addEventListener("change", handleChange);

        // Return cleanup function
        return () => {
          mediaQuery.removeEventListener("change", handleChange);
        };
      },

      updateMetaThemeColor: (theme) => {
        if (typeof window === "undefined") {
          return;
        }

        const metaThemeColor = document.querySelector(
          'meta[name="theme-color"]',
        );
        if (metaThemeColor) {
          const color = theme === "dark" ? "#0f172a" : "#ffffff";
          metaThemeColor.setAttribute("content", color);
        }
      },
    }),
    {
      name: "insight-flow-theme",
      partialize: (state) => ({
        theme: state.theme,
      }),
    },
  ),
);

// ===========================================
// Theme Store Selectors
// ===========================================

export const themeSelectors = {
  // Get current theme
  getTheme: (state: ThemeState) => state.theme,
  getCurrentTheme: (state: ThemeState) => state.currentTheme, // Alias

  // Get resolved theme (actual applied theme)
  getResolvedTheme: (state: ThemeState) => state.resolvedTheme,

  // Check if dark theme is active
  isDark: (state: ThemeState) => state.resolvedTheme === "dark",

  // Check if light theme is active
  isLight: (state: ThemeState) => state.resolvedTheme === "light",

  // Check if theme is system
  isSystem: (state: ThemeState) => state.theme === "system",

  // Check if theme transition is in progress
  isTransitioning: (state: ThemeState) => state.isTransitioning,

  // Compatibility selectors
  systemPrefersDark: (state: ThemeState) => state.systemPrefersDark,
  isSystemMode: (state: ThemeState) => state.isSystemMode,
  availableThemes: (state: ThemeState) => state.availableThemes,
  colorScheme: (state: ThemeState) => state.colorScheme,
  nextTheme: (state: ThemeState) => state.nextTheme,

  // Get theme status object
  getThemeStatus: (state: ThemeState) => ({
    theme: state.theme,
    currentTheme: state.currentTheme,
    resolvedTheme: state.resolvedTheme,
    systemPrefersDark: state.systemPrefersDark,
    isSystemMode: state.isSystemMode,
    isDark: state.resolvedTheme === "dark",
    isLight: state.resolvedTheme === "light",
    isSystem: state.theme === "system",
    isTransitioning: state.isTransitioning,
    availableThemes: state.availableThemes,
    colorScheme: state.colorScheme,
    nextTheme: state.nextTheme,
    primaryColor: state.primaryColor,
  }),
} as const;

// ===========================================
// Theme Store Actions
// ===========================================

export const themeActions = {
  // Initialize theme on app start
  init: () => {
    const { initializeTheme } = useThemeStore.getState();
    initializeTheme();
  },

  // Set theme with transition
  setThemeWithTransition: (theme: Theme) => {
    const { setTransitioning, setTheme } = useThemeStore.getState();

    setTransitioning(true);

    // Add transition class
    if (typeof window !== "undefined") {
      document.documentElement.classList.add("theme-transitioning");
    }

    setTheme(theme);

    // Remove transition class after animation
    setTimeout(() => {
      setTransitioning(false);
      if (typeof window !== "undefined") {
        document.documentElement.classList.remove("theme-transitioning");
      }
    }, 300);
  },

  // Toggle theme with transition
  toggleThemeWithTransition: () => {
    const { theme } = useThemeStore.getState();
    const newTheme = theme === "light" ? "dark" : "light";
    themeActions.setThemeWithTransition(newTheme);
  },

  // Get theme icon name
  getThemeIcon: (theme: "light" | "dark" | "system" = "system") => {
    const { resolvedTheme, isSystem } = useThemeStore.getState();

    if (isSystem) {
      return resolvedTheme === "dark" ? "Sun" : "Moon";
    }

    return theme === "dark" ? "Sun" : "Moon";
  },

  // Get theme label
  getThemeLabel: (theme: Theme) => {
    const labels = {
      light: "Light",
      dark: "Dark",
      system: "System",
    };
    return labels[theme];
  },

  // Check if theme supports transitions
  supportsTransitions: () => {
    if (typeof window === "undefined") {
      return false;
    }

    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    return !reducedMotion.matches;
  },
};

// ===========================================
// CSS for theme transitions
export const themeTransitionStyles = `
  .theme-transitioning * {
    transition: background-color 0.3s ease,
                border-color 0.3s ease,
                color 0.3s ease,
                fill 0.3s ease,
                stroke 0.3s ease !important;
 }
`;
