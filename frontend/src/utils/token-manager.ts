/**
 * Token Manager - Security Notice
 * 
 * IMPORTANT: This file previously stored tokens in localStorage which is
 * vulnerable to XSS attacks. Authentication tokens are now ONLY stored in
 * HttpOnly cookies managed by the backend for security.
 * 
 * This file is kept for backwards compatibility and cleanup purposes only.
 * - getAccessToken/getRefreshToken: Return null (tokens are in HttpOnly cookies)
 * - setTokens: No-op (tokens are set by backend via Set-Cookie)
 * - clearTokens: Clears any legacy storage and auth state
 * 
 * The actual token management is handled by:
 * - Backend: utils/token_utils.py (creates and sets HttpOnly cookies)
 * - Frontend: API calls with credentials: 'include' (sends cookies automatically)
 */

import type { User } from "../types";

export class TokenManager {
  private static readonly ACCESS_TOKEN_KEY = "access_token";
  private static readonly REFRESH_TOKEN_KEY = "refresh_token";
  private static readonly USER_KEY = "user";
  private static readonly AUTH_STORAGE_KEY = "insight-flow-auth";

  /**
   * Get access token.
   * 
   * Security Note: Access tokens are now stored in HttpOnly cookies
   * and are not accessible from JavaScript (protection against XSS).
   * This method returns null - authentication is handled via cookies.
   * 
   * @returns null (tokens are in HttpOnly cookies, not accessible from JS)
   */
  static getAccessToken(): string | null {
    // Security: Tokens are now in HttpOnly cookies, not accessible from JS
    return null;
  }

  /**
   * Get refresh token.
   * 
   * Security Note: Refresh tokens are stored in HttpOnly cookies
   * and are not accessible from JavaScript.
   * 
   * @returns null (tokens are in HttpOnly cookies, not accessible from JS)
   */
  static getRefreshToken(): string | null {
    // Security: Tokens are now in HttpOnly cookies, not accessible from JS
    return null;
  }

  /**
   * Set tokens - No-op for security.
   * 
   * Security Note: This method is intentionally a no-op. Tokens should
   * NEVER be stored in localStorage due to XSS vulnerability. The backend
   * sets tokens as HttpOnly cookies which are automatically sent with requests.
   * 
   * @deprecated Tokens are set by the backend via Set-Cookie headers
   */
  static setTokens(_accessToken: string, _refreshToken: string): void {
    // Security: Do NOT store tokens in localStorage - they are vulnerable to XSS
    // The backend sets HttpOnly cookies which are secure
    console.warn(
      "[TokenManager] setTokens called but tokens are managed via HttpOnly cookies. " +
      "This call has no effect for security reasons."
    );
  }

  /**
   * Clear all authentication-related storage.
   * 
   * This clears any legacy localStorage entries and the zustand persist storage.
   * The actual HttpOnly cookies are cleared by calling the backend /auth/logout endpoint.
   */
  static clearTokens(): void {
    if (typeof window === "undefined") {
      return;
    }
    
    // Clear any legacy tokens that might exist from before the security update
    try {
      localStorage.removeItem(this.ACCESS_TOKEN_KEY);
      localStorage.removeItem(this.REFRESH_TOKEN_KEY);
      localStorage.removeItem(this.USER_KEY);
      localStorage.removeItem(this.AUTH_STORAGE_KEY);
    } catch (e) {
      // Ignore errors - localStorage might not be available
      console.warn("[TokenManager] Failed to clear legacy storage", e);
    }
    
    // Note: HttpOnly cookies are cleared by calling the backend /auth/logout endpoint
    // which sets the cookies with max-age=0
  }

  /**
   * Get cached user from localStorage.
   * 
   * This is used for UI purposes only (showing user info before API call completes).
   * The actual authentication state is verified via the /auth/me API call.
   * 
   * @returns User object if cached, null otherwise
   */
  static getUser(): User | null {
    if (typeof window === "undefined") {
      return null;
    }
    
    try {
      // Check zustand persist storage first
      const authState = localStorage.getItem(this.AUTH_STORAGE_KEY);
      if (authState) {
        const parsed = JSON.parse(authState);
        if (parsed?.state?.user) {
          return parsed.state.user;
        }
      }
      
      // Fallback to legacy user key
      const userStr = localStorage.getItem(this.USER_KEY);
      return userStr ? JSON.parse(userStr) : null;
    } catch {
      return null;
    }
  }

  /**
   * Check if user appears to be authenticated (based on cached state).
   * 
   * Note: This is for optimistic UI only. Actual auth status is determined
   * by the /auth/me API call which validates the HttpOnly cookie.
   * 
   * @returns true if there's cached user data
   */
  static hasAuthState(): boolean {
    return this.getUser() != null;
  }
}

/**
 * Security Documentation
 * =====================
 * 
 * Why HttpOnly Cookies Instead of localStorage?
 * 
 * 1. XSS Protection: HttpOnly cookies cannot be accessed by JavaScript,
 *    so even if an XSS vulnerability exists, tokens cannot be stolen.
 * 
 * 2. Automatic Handling: Cookies are automatically sent with requests
 *    and don't need explicit header management in fetch calls.
 * 
 * 3. Server Control: The server controls when cookies expire and can
 *    revoke them by blacklisting the token ID (jti).
 * 
 * How Authentication Works:
 * 
 * 1. Login → Backend sets access_token and refresh_token as HttpOnly cookies
 * 2. API Calls → Browser automatically sends cookies with credentials: 'include'
 * 3. Refresh → Backend reads refresh_token cookie, issues new tokens as cookies
 * 4. Logout → Backend clears cookies (max-age=0) and blacklists tokens
 * 
 * Frontend Configuration:
 * 
 * All API calls must include: credentials: 'include'
 * This is configured in the API client (lib/api-client.ts)
 */
