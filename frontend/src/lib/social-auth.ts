const DEFAULT_APP_URL = "http://localhost:3000";
const OAUTH_STATE_BYTES = 16;

function getAppBaseUrl(): string {
  return (process.env.NEXT_PUBLIC_APP_URL ?? DEFAULT_APP_URL).replace(/\/+$/, "");
}

export function getGitHubRedirectUri(): string {
  return `${getAppBaseUrl()}/auth/callback/github`;
}

export function createOAuthState(): string {
  const bytes = new Uint8Array(OAUTH_STATE_BYTES);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
}
