import { resolveAppUrl } from "@/lib/app-url";

const OAUTH_STATE_BYTES = 16;

function getAppBaseUrl(): string {
  return resolveAppUrl({
    browserOrigin:
      typeof window !== "undefined" ? window.location.origin : undefined,
  });
}

export function getGitHubRedirectUri(): string {
  return `${getAppBaseUrl()}/auth/callback/github`;
}

export function createOAuthState(): string {
  const bytes = new Uint8Array(OAUTH_STATE_BYTES);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
}
