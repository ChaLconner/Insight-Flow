type AuthenticatedCacheClearer = () => void | Promise<void>;

const authenticatedCacheClearers = new Set<AuthenticatedCacheClearer>();

/**
 * Register a module-level cache that contains authenticated data.
 *
 * Modules register lazily when loaded, so clearing auth state does not need to
 * import every feature and create circular dependencies.
 */
export function registerAuthenticatedCacheClearer(
  clearer: AuthenticatedCacheClearer,
): () => void {
  authenticatedCacheClearers.add(clearer);
  return () => authenticatedCacheClearers.delete(clearer);
}

/** Clear every registered authenticated cache on login, logout, or expiry. */
export async function clearAuthenticatedCaches(): Promise<void> {
  const results = await Promise.allSettled(
    [...authenticatedCacheClearers].map((clearer) => Promise.resolve(clearer())),
  );

  for (const result of results) {
    if (result.status === "rejected") {
      console.warn("Failed to clear authenticated cache", result.reason);
    }
  }
}
