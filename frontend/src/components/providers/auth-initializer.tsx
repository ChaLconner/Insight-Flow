"use client";

import { useEffect, useRef } from "react";
import { usePathname } from "next/navigation";
import { useAuthStore } from "@/stores/auth-store";

export function AuthInitializer() {
  const initializeAuth = useAuthStore((state) => state.initializeAuth);
  const pathname = usePathname();
  const isInitialized = useRef(false);

  useEffect(() => {
    // Middleware protects private routes. Public and auth pages do not need a
    // session verification round-trip just to render their static content.
    // The effect runs again when App Router navigation enters a protected
    // route, so the session is still initialized before private data loads.
    const isPublicOrAuthRoute =
      pathname === "/" || pathname?.startsWith("/auth/");

    if (isPublicOrAuthRoute) {
      return;
    }

    if (!isInitialized.current) {
      isInitialized.current = true;
      initializeAuth();
    }
  }, [initializeAuth, pathname]);

  return null;
}
