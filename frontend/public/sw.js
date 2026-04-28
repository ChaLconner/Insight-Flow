/**
 * Insight Flow Service Worker
 * Provides offline support and caching for better performance.
 */

/* eslint-env serviceworker */
/* global self, caches, fetch, URL, console */

var CACHE_NAME = "insight-flow-v1";
var STATIC_CACHE_NAME = "insight-flow-static-v1";
var API_CACHE_NAME = "insight-flow-api-v1";

// Static assets to cache on install
var STATIC_ASSETS = [
  "/",
  "/dashboard",
  "/auth/login",
  "/manifest.json",
];

// Do not cache authenticated API responses. HttpOnly-cookie auth makes cache
// entries user-sensitive, while Cache Storage keys do not include current user.
var CACHEABLE_API_PATTERNS = [
];

// Install event - cache static assets
self.addEventListener("install", function(event) {
  event.waitUntil(
    caches.open(STATIC_CACHE_NAME).then(function(cache) {
      console.log("[SW] Caching static assets");
      return cache.addAll(STATIC_ASSETS).catch(function(error) {
        console.warn("[SW] Failed to cache some static assets:", error);
      });
    })
  );
  // Activate immediately
  self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener("activate", function(event) {
  event.waitUntil(
    caches.keys().then(function(cacheNames) {
      return Promise.all(
        cacheNames
          .filter(function(name) {
            return (
              name.startsWith("insight-flow-") &&
              name !== CACHE_NAME &&
              name !== STATIC_CACHE_NAME &&
              name !== API_CACHE_NAME
            );
          })
          .map(function(name) {
            console.log("[SW] Deleting old cache:", name);
            return caches.delete(name);
          })
      );
    })
  );
  // Claim all clients immediately
  self.clients.claim();
});

// Check if URL is a static asset
function isStaticAsset(pathname) {
  return (
    pathname.startsWith("/_next/static/") ||
    pathname.startsWith("/static/") ||
    pathname.match(/\.(js|css|woff2?|ttf|eot|svg|png|jpg|jpeg|gif|webp|avif|ico)$/) !== null
  );
}

// Check if API request should be cached
function shouldCacheApiRequest(pathname) {
  return CACHEABLE_API_PATTERNS.some(function(pattern) {
    return pattern.test(pathname);
  });
}

// Cache first, then network strategy
function cacheFirstWithNetwork(request, cacheName) {
  return caches.open(cacheName).then(function(cache) {
    return cache.match(request).then(function(cachedResponse) {
      if (cachedResponse) {
        // Return cached response, but update cache in background
        updateCache(request, cacheName);
        return cachedResponse;
      }

      return fetch(request).then(function(networkResponse) {
        if (networkResponse.ok) {
          cache.put(request, networkResponse.clone());
        }
        return networkResponse;
      }).catch(function() {
        // Return offline fallback for HTML requests
        if (request.headers.get("accept") && request.headers.get("accept").includes("text/html")) {
          return cache.match("/");
        }
        throw new Error("Network request failed and no cache available");
      });
    });
  });
}

// Network first, then cache strategy
function networkFirstWithCache(request, cacheName) {
  return caches.open(cacheName).then(function(cache) {
    return fetch(request).then(function(networkResponse) {
      if (networkResponse.ok) {
        cache.put(request, networkResponse.clone());
      }
      return networkResponse;
    }).catch(function() {
      // Try to return cached response
      return cache.match(request).then(function(cachedResponse) {
        if (cachedResponse) {
          console.log("[SW] Serving from cache:", request.url);
          return cachedResponse;
        }
        throw new Error("Network request failed and no cache available");
      });
    });
  });
}

// Update cache in background
function updateCache(request, cacheName) {
  caches.open(cacheName).then(function(cache) {
    fetch(request).then(function(networkResponse) {
      if (networkResponse.ok) {
        cache.put(request, networkResponse);
      }
    }).catch(function() {
      // Silently fail - cache update is best-effort
    });
  });
}

// Fetch event - handle requests
self.addEventListener("fetch", function(event) {
  var request = event.request;
  var url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== "GET") {
    return;
  }

  // Skip chrome-extension and other non-http(s) requests
  if (!url.protocol.startsWith("http")) {
    return;
  }

  // API requests - Network first, then cache
  if (url.pathname.startsWith("/api/") || url.hostname !== self.location.hostname) {
    if (shouldCacheApiRequest(url.pathname)) {
      event.respondWith(networkFirstWithCache(request, API_CACHE_NAME));
    }
    return;
  }

  // Static assets - Cache first, then network
  if (isStaticAsset(url.pathname)) {
    event.respondWith(cacheFirstWithNetwork(request, STATIC_CACHE_NAME));
    return;
  }

  // HTML pages - Network first for freshness
  if (request.headers.get("accept") && request.headers.get("accept").includes("text/html")) {
    event.respondWith(networkFirstWithCache(request, STATIC_CACHE_NAME));
    return;
  }
});

// Handle messages from the main thread
self.addEventListener("message", function(event) {
  if (event.data && event.data.type === "SKIP_WAITING") {
    self.skipWaiting();
  }

  if (event.data && event.data.type === "CLEAR_CACHE") {
    event.waitUntil(
      caches.keys().then(function(names) {
        return Promise.all(names.map(function(name) {
          return caches.delete(name);
        }));
      })
    );
  }
});
