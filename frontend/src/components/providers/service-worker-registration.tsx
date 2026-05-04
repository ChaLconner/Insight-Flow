"use client";

import { useEffect } from "react";

/**
 * Service Worker Registration Component
 * Registers the service worker for offline support and caching.
 * Only registers in production to avoid caching issues during development.
 */
export function ServiceWorkerRegistration() {
  useEffect(() => {
    if (
      process.env.NODE_ENV !== "production" &&
      typeof window !== "undefined" &&
      "serviceWorker" in navigator
    ) {
      unregisterDevelopmentServiceWorkers();
      return;
    }

    // Only register in production and if service workers are supported
    if (
      process.env.NODE_ENV === "production" &&
      typeof window !== "undefined" &&
      "serviceWorker" in navigator
    ) {
      registerServiceWorker();
    }
  }, []);

  return null;
}

async function unregisterDevelopmentServiceWorkers() {
  try {
    const registrations = await navigator.serviceWorker.getRegistrations();
    await Promise.all(registrations.map((registration) => registration.unregister()));
    await clearServiceWorkerCache();
  } catch (error) {
    console.warn("[SW] Failed to clear development service workers:", error);
  }
}

async function registerServiceWorker() {
  try {
    const registration = await navigator.serviceWorker.register("/sw.js", {
      scope: "/",
      updateViaCache: "none",
    });

    // Check for updates periodically without adding constant foreground traffic.
    setInterval(() => {
      registration.update();
    }, 6 * 60 * 60 * 1000);

    // Handle updates
    registration.addEventListener("updatefound", () => {
      const newWorker = registration.installing;
      if (!newWorker) {
        return;
      }

      newWorker.addEventListener("statechange", () => {
        if (newWorker.state === "installed" && navigator.serviceWorker.controller) {
          // New service worker is ready, but old one is still serving
          // Could show a "Update available" toast here if needed
        }
      });
    });
  } catch (error) {
    // Only warn on failure - important for debugging production issues
    if (process.env.NODE_ENV === "production") {
      console.warn("[SW] Service Worker registration failed:", error);
    }
  }
}

/**
 * Utility to clear service worker caches
 * Call this when user logs out or when you need to clear cached data
 */
export async function clearServiceWorkerCache(): Promise<void> {
  if ("serviceWorker" in navigator && navigator.serviceWorker.controller) {
    await new Promise<void>((resolve) => {
      const channel = new MessageChannel();
      const timeout = window.setTimeout(resolve, 1000);

      channel.port1.onmessage = () => {
        window.clearTimeout(timeout);
        resolve();
      };

      navigator.serviceWorker.controller?.postMessage(
        { type: "CLEAR_CACHE" },
        [channel.port2],
      );
    });
  }

  if ("caches" in window) {
    const cacheNames = await caches.keys();
    await Promise.all(
      cacheNames
        .filter((name) => name.startsWith("insight-flow-"))
        .map((name) => caches.delete(name)),
    );
  }
}

/**
 * Utility to force service worker update
 */
export async function updateServiceWorker(): Promise<void> {
  if ("serviceWorker" in navigator) {
    const registration = await navigator.serviceWorker.getRegistration();
    if (registration) {
      await registration.update();
      if (registration.waiting) {
        registration.waiting.postMessage({ type: "SKIP_WAITING" });
      }
    }
  }
}

export default ServiceWorkerRegistration;
