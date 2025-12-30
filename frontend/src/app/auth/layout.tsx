"use client";

import { useLayoutEffect, useEffect, useRef } from "react";
import { GoogleAuthProvider } from "@/providers/google-auth-provider";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const originalThemeRef = useRef<{
    wasLight: boolean;
    wasDark: boolean;
  } | null>(null);

  // Use useLayoutEffect for immediate execution before paint
  useLayoutEffect(() => {
    const root = document.documentElement;

    // Store original theme classes (only once)
    originalThemeRef.current ??= {
      wasLight: root.classList.contains("light"),
      wasDark: root.classList.contains("dark"),
    };

    // Force dark theme immediately
    root.classList.remove("light", "system");
    root.classList.add("dark");
    root.style.colorScheme = "dark";
    root.setAttribute("data-theme", "dark");
    root.setAttribute("data-color-scheme", "dark");
  }, []);

  // Set up MutationObserver to prevent any theme changes while on auth pages
  useEffect(() => {
    const root = document.documentElement;

    // Create observer to prevent theme class changes
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.attributeName === "class") {
          // If theme got changed away from dark, force it back
          if (!root.classList.contains("dark") || root.classList.contains("light")) {
            root.classList.remove("light", "system");
            root.classList.add("dark");
            root.style.colorScheme = "dark";
          }
        }
      });
    });

    observer.observe(root, {
      attributes: true,
      attributeFilter: ["class"],
    });

    // Cleanup: restore original theme when leaving auth pages
    return () => {
      observer.disconnect();

      const original = originalThemeRef.current;
      if (original?.wasLight) {
        root.classList.remove("dark");
        root.classList.add("light");
        root.style.colorScheme = "light";
      }
      // If was dark or no class set, let the theme system handle it
    };
  }, []);

  return (
    <div className="min-h-screen bg-background text-foreground selection:bg-primary/30">
      <GoogleAuthProvider>{children}</GoogleAuthProvider>
    </div>
  );
}
