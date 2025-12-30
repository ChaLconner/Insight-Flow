import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * Middleware for authentication and route protection
 * Runs on the Edge runtime for fast response times
 */

// Public routes that don't require authentication
const PUBLIC_ROUTES = [
  "/auth/login",
  "/auth/register",
  "/auth/forgot-password",
  "/auth/reset-password",
  "/auth/callback",
];

// Routes that should redirect to dashboard if already authenticated
const AUTH_ROUTES = ["/auth/login", "/auth/register"];

// Static assets and API routes to skip
const SKIP_ROUTES = [
  "/_next",
  "/api",
  "/favicon.ico",
  "/manifest.json",
  "/icon.svg",
  "/apple-icon.svg",
];

/**
 * Basic JWT validation for Edge runtime.
 * Checks if token has valid format and is not expired.
 * Note: This doesn't verify signature (that's done server-side).
 */
function isTokenValid(token: string): boolean {
  try {
    // JWT format: header.payload.signature
    const parts = token.split(".");
    if (parts.length !== 3) {
      return false;
    }

    // Decode payload (base64url)
    const payload = parts[1];
    const decoded = JSON.parse(atob(payload.replace(/-/g, "+").replace(/_/g, "/")));

    // Check expiration
    if (decoded.exp) {
      const expiry = decoded.exp * 1000; // Convert to milliseconds
      if (Date.now() >= expiry) {
        return false;
      }
    }

    return true;
  } catch {
    return false;
  }
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Skip middleware for static assets and API routes
  if (SKIP_ROUTES.some((route) => pathname.startsWith(route))) {
    return NextResponse.next();
  }

  // Get auth token from cookies and validate
  const accessToken = request.cookies.get("access_token")?.value;
  const isAuthenticated = accessToken ? isTokenValid(accessToken) : false;


  // Check if the current path is a public route
  const isPublicRoute = PUBLIC_ROUTES.some(
    (route) => pathname === route || pathname.startsWith(`${route}/`),
  );

  // Check if the current path is an auth route (login/register)
  const isAuthRoute = AUTH_ROUTES.some(
    (route) => pathname === route || pathname.startsWith(`${route}/`),
  );

  // If authenticated and trying to access auth routes, redirect to dashboard
  if (isAuthenticated && isAuthRoute) {
    const dashboardUrl = new URL("/dashboard", request.url);
    return NextResponse.redirect(dashboardUrl);
  }

  // If not authenticated and trying to access protected routes
  if (!isAuthenticated && !isPublicRoute) {
    const loginUrl = new URL("/auth/login", request.url);

    // Add the current path as a redirect parameter (optional)
    if (pathname !== "/" && pathname !== "/dashboard") {
      loginUrl.searchParams.set("redirect", pathname);
    }

    return NextResponse.redirect(loginUrl);
  }

  // Handle root path redirect
  if (pathname === "/") {
    if (isAuthenticated) {
      return NextResponse.redirect(new URL("/dashboard", request.url));
    } else {
      return NextResponse.redirect(new URL("/auth/login", request.url));
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public folder
     */
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
