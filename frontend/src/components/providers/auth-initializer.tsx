"use client";

import { useEffect, useRef } from "react";
import { useAuthStore } from "@/stores/auth-store";

export function AuthInitializer() {
  const initializeAuth = useAuthStore((state) => state.initializeAuth);
  const isInitialized = useRef(false);

  useEffect(() => {
    if (!isInitialized.current) {
      isInitialized.current = true;
      initializeAuth();
    }
  }, [initializeAuth]);

  return null;
}
