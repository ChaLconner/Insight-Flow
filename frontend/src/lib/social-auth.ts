const DEFAULT_APP_URL = "http://localhost:3000";
const OAUTH_STATE_BYTES = 16;

function getAppBaseUrl(): string {
  const configuredAppUrl = process.env.NEXT_PUBLIC_APP_URL?.trim();
  const browserOrigin =
    typeof window !== "undefined" ? window.location.origin : undefined;
  const appUrl =
    configuredAppUrl !== undefined && configuredAppUrl !== ""
      ? configuredAppUrl
      : (browserOrigin ?? DEFAULT_APP_URL);

  return appUrl.replace(/\/+$/, "");
}

export function getGitHubRedirectUri(): string {
  return `${getAppBaseUrl()}/auth/callback/github`;
}

export function createOAuthState(): string {
  const bytes = new Uint8Array(OAUTH_STATE_BYTES);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
}
