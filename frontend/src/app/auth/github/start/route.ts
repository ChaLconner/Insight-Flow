import { NextResponse, type NextRequest } from "next/server";

const GITHUB_OAUTH_STATE_KEY = "github_oauth_state";
const GITHUB_OAUTH_REDIRECT_KEY = "github_oauth_redirect";
const OAUTH_STATE_BYTES = 16;

function createOAuthState(): string {
  const bytes = new Uint8Array(OAUTH_STATE_BYTES);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
}

function getAppBaseUrl(request: NextRequest): string {
  const configuredAppUrl = process.env.NEXT_PUBLIC_APP_URL?.trim();
  const appUrl =
    configuredAppUrl !== undefined && configuredAppUrl !== ""
      ? configuredAppUrl
      : request.nextUrl.origin;

  return appUrl.replace(/\/+$/, "");
}

function getSafeRedirect(value: string | null): string | null {
  if (!value || !value.startsWith("/") || value.startsWith("//")) {
    return null;
  }

  return value;
}

export function GET(request: NextRequest) {
  const clientId = process.env.NEXT_PUBLIC_GITHUB_CLIENT_ID;
  const loginUrl = new URL("/auth/login", request.url);

  if (!clientId) {
    loginUrl.searchParams.set("message", "GitHub login is not configured");
    return NextResponse.redirect(loginUrl);
  }

  const state = createOAuthState();
  const redirectUri = `${getAppBaseUrl(request)}/auth/callback/github`;
  const githubUrl = new URL("https://github.com/login/oauth/authorize");
  githubUrl.searchParams.set("client_id", clientId);
  githubUrl.searchParams.set("redirect_uri", redirectUri);
  githubUrl.searchParams.set("scope", "read:user user:email");
  githubUrl.searchParams.set("state", state);

  const response = NextResponse.redirect(githubUrl);
  const cookieOptions = {
    maxAge: 10 * 60,
    path: "/auth/callback/github",
    sameSite: "lax" as const,
    secure: request.nextUrl.protocol === "https:",
  };
  response.cookies.set(GITHUB_OAUTH_STATE_KEY, state, cookieOptions);

  const requestedRedirect = getSafeRedirect(
    request.nextUrl.searchParams.get("redirect"),
  );
  if (requestedRedirect) {
    response.cookies.set(
      GITHUB_OAUTH_REDIRECT_KEY,
      requestedRedirect,
      cookieOptions,
    );
  }

  return response;
}
