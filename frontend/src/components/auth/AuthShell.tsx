"use client";

import { useEffect, useLayoutEffect, useRef } from "react";
import { GoogleAuthProvider } from "@/providers/google-auth-provider";
import {
  AnimatedBackground,
  FloatingShapes,
} from "@/components/ui/animated-background";

export function AuthShell({ children }: { children: React.ReactNode }) {
  const originalThemeRef = useRef<{
    className: string;
    colorScheme: string;
    dataTheme: string | null;
    dataColorScheme: string | null;
  } | null>(null);

  const applyAuthTheme = () => {
    const root = document.documentElement;

    root.classList.remove("light", "system");
    root.classList.add("dark");
    root.style.colorScheme = "dark";
    root.setAttribute("data-theme", "dark");
    root.setAttribute("data-color-scheme", "dark");
  };

  useEffect(() => {
    const handlePageShow = (e: PageTransitionEvent) => {
      if (e.persisted) {
        // Page was restored from bfcache. React's event delegation,
        // canvas animations, and Google SDK iframes are all in a broken
        // frozen state. The only reliable recovery is a full page reload.
        // Use setTimeout to avoid browsers blocking synchronous navigation
        // during page restoration.
        setTimeout(() => window.location.reload(), 0);
        return;
      }
      applyAuthTheme();
    };

    const handleFocus = () => {
      applyAuthTheme();
    };

    window.addEventListener("pageshow", handlePageShow);
    window.addEventListener("focus", handleFocus);

    return () => {
      window.removeEventListener("pageshow", handlePageShow);
      window.removeEventListener("focus", handleFocus);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Use useLayoutEffect for immediate execution before paint
  useLayoutEffect(() => {
    const root = document.documentElement;

    // Store original theme classes (only once)
    originalThemeRef.current ??= {
      className: root.className,
      colorScheme: root.style.colorScheme,
      dataTheme: root.getAttribute("data-theme"),
      dataColorScheme: root.getAttribute("data-color-scheme"),
    };

    applyAuthTheme();

    // Reset body overflow – a Dialog or modal from a previous page may
    // have left `overflow: hidden` on the body, blocking all interaction.
    document.body.style.overflow = "";
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Set up MutationObserver to prevent any theme changes while on auth pages
  useEffect(() => {
    const root = document.documentElement;

    // Create observer to prevent theme class changes
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (
          mutation.attributeName === "class" ||
          mutation.attributeName === "style" ||
          mutation.attributeName === "data-theme" ||
          mutation.attributeName === "data-color-scheme"
        ) {
          // If theme got changed away from dark, force it back
          if (
            !root.classList.contains("dark") ||
            root.classList.contains("light") ||
            root.style.colorScheme !== "dark" ||
            root.getAttribute("data-theme") !== "dark" ||
            root.getAttribute("data-color-scheme") !== "dark"
          ) {
            applyAuthTheme();
          }
        }
      });
    });

    observer.observe(root, {
      attributes: true,
      attributeFilter: ["class", "style", "data-theme", "data-color-scheme"],
    });

    // Cleanup: restore original theme when leaving auth pages
    return () => {
      observer.disconnect();

      const original = originalThemeRef.current;
      if (!original) {
        return;
      }

      root.className = original.className;
      root.style.colorScheme = original.colorScheme;

      if (original.dataTheme == null) {
        root.removeAttribute("data-theme");
      } else {
        root.setAttribute("data-theme", original.dataTheme);
      }

      if (original.dataColorScheme == null) {
        root.removeAttribute("data-color-scheme");
      } else {
        root.setAttribute("data-color-scheme", original.dataColorScheme);
      }
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="relative min-h-screen overflow-hidden bg-background text-foreground selection:bg-primary/30">
      <div className="auth-particle-fallback" aria-hidden="true" />
      <AnimatedBackground />
      <FloatingShapes />
      <div className="relative z-20 min-h-screen">
        <GoogleAuthProvider>{children}</GoogleAuthProvider>
      </div>
    </div>
  );
}
