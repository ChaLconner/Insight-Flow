// ===========================================
// Theme Provider Component
// ===========================================

"use client";

import { useEffect, useRef, type ReactNode } from "react";
import { usePathname } from "next/navigation";
import { useTheme } from "@/hooks/use-theme";
import { useIsHydrated } from "@/hooks/use-hydration";

import { useThemeStore } from "@/stores/theme-store";
import { useAuthStore } from "@/stores/auth-store";
import { usersApi } from "@/lib/api-endpoints";

interface ThemeProviderProps {
  children: ReactNode;
  defaultTheme?: "light" | "dark" | "system";
  storageKey?: string;
}

export function ThemeProvider({
  children,
  // defaultTheme = "system",
  // storageKey = "insight-flow-theme",
}: ThemeProviderProps) {
  const { initializeTheme, currentTheme } = useTheme();
  const isHydrated = useIsHydrated();
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const lastSyncedThemeRef = useRef<string | null>(null);

  // Check if on auth pages - skip theme operations
  const pathname = usePathname();
  const isAuthPage = pathname?.startsWith("/auth");

  // Only run theme operations after hydration to prevent mismatch
  useEffect(() => {
    // Skip theme initialization on auth pages
    if (isHydrated && !isAuthPage) {
      // Initialize theme only once after hydration
      initializeTheme();
    }
  }, [isHydrated, initializeTheme, isAuthPage]);

  // Sync theme with server (DB)
  useEffect(() => {
    // Skip syncing on auth pages
    if (!isHydrated || !isAuthenticated || isAuthPage) {
      return;
    }

    if (lastSyncedThemeRef.current === null) {
      lastSyncedThemeRef.current = currentTheme;
      return;
    }

    if (lastSyncedThemeRef.current === currentTheme) {
      return;
    }

    // Debounce save to prevent excessive API calls
    const timer = setTimeout(() => {
      usersApi
        .updateSettings({ theme: currentTheme })
        .then(() => {
          lastSyncedThemeRef.current = currentTheme;
        })
        .catch((err) => console.warn("Failed to sync theme:", err));
    }, 2000);

    return () => clearTimeout(timer);
  }, [currentTheme, isHydrated, isAuthenticated, isAuthPage]);

  // Safety net: Ensure theme class is applied if missing
  useEffect(() => {
    // Skip on auth pages
    if (!isHydrated || isAuthPage) {
      return;
    }

    const root = document.documentElement;
    if (!root.classList.contains("light") && !root.classList.contains("dark")) {
      const storedTheme = useThemeStore.getState().theme;
      if (storedTheme === "light") {
        root.classList.add("light");
        root.style.colorScheme = "light";
      } else if (storedTheme === "dark") {
        root.classList.add("dark");
        root.style.colorScheme = "dark";
      } else {
        // System or other
         const isDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
         root.classList.add(isDark ? "dark" : "light");
         root.style.colorScheme = isDark ? "dark" : "light";
      }
    }
  }, [isHydrated, isAuthPage]);

  // Don't render anything until hydrated to prevent hydration mismatch
  // if (!isHydrated) {
  //   return null;
  // }

  return <>{children}</>;
}

export default ThemeProvider;
