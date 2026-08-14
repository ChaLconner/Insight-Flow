"use client";

import dynamic from "next/dynamic";
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { isE2ERuntime } from "@/lib/runtime-flags";

const AuthBackground = dynamic(
  () =>
    import("@/components/auth/AuthBackground").then(
      (module) => module.AuthBackground,
    ),
  { ssr: false },
);

export function AuthShell({ children }: Readonly<{ children: React.ReactNode }>) {
  const [showAnimatedBackground, setShowAnimatedBackground] = useState(false);
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
    root.dataset.theme = "dark";
    root.dataset.colorScheme = "dark";
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
   
  }, []);

  useEffect(() => {
    if (isE2ERuntime()) {
      return;
    }

    const timeoutId = window.setTimeout(() => {
      setShowAnimatedBackground(true);
    }, 2000);

    return () => window.clearTimeout(timeoutId);
  }, []);

  // Use useLayoutEffect for immediate execution before paint
  useLayoutEffect(() => {
    const root = document.documentElement;

    // Store original theme classes (only once)
    originalThemeRef.current ??= {
      className: root.className,
      colorScheme: root.style.colorScheme,
      dataTheme: root.dataset.theme ?? null,
      dataColorScheme: root.dataset.colorScheme ?? null,
    };

    applyAuthTheme();

    // Reset body overflow – a Dialog or modal from a previous page may
    // have left `overflow: hidden` on the body, blocking all interaction.
    document.body.style.overflow = "";
   
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
            root.dataset.theme !== "dark" ||
            root.dataset.colorScheme !== "dark"
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
        delete root.dataset.theme;
      } else {
        root.dataset.theme = original.dataTheme;
      }

      if (original.dataColorScheme == null) {
        delete root.dataset.colorScheme;
      } else {
        root.dataset.colorScheme = original.dataColorScheme;
      }
    };
   
  }, []);

  return (
    <div className="relative min-h-screen overflow-hidden bg-background text-foreground selection:bg-primary/30">
      <div className="auth-particle-fallback" aria-hidden="true" />
      {showAnimatedBackground ? <AuthBackground /> : null}
      <div className="relative z-20 min-h-screen">
        <main id="main-content" tabIndex={-1}>
          {children}
        </main>
      </div>
    </div>
  );
}
