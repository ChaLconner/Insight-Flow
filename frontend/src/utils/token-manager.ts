export class TokenManager {
    private static readonly ACCESS_TOKEN_KEY = 'access_token';
    private static readonly REFRESH_TOKEN_KEY = 'refresh_token';
    private static readonly USER_KEY = 'user';
    private static readonly AUTH_STORAGE_KEY = 'insight-flow-auth';

    static getAccessToken(): string | null {
        if (typeof window === 'undefined') return null;
        return localStorage.getItem(this.ACCESS_TOKEN_KEY);
    }

    static getRefreshToken(): string | null {
        if (typeof window === 'undefined') return null;
        return localStorage.getItem(this.REFRESH_TOKEN_KEY);
    }

    static setTokens(accessToken: string, refreshToken: string): void {
        if (typeof window === 'undefined') return;
        localStorage.setItem(this.ACCESS_TOKEN_KEY, accessToken);
        localStorage.setItem(this.REFRESH_TOKEN_KEY, refreshToken);
    }

    static clearTokens(): void {
        if (typeof window === 'undefined') return;
        localStorage.removeItem(this.ACCESS_TOKEN_KEY);
        localStorage.removeItem(this.REFRESH_TOKEN_KEY);
        localStorage.removeItem(this.USER_KEY);
        try {
            localStorage.removeItem(this.AUTH_STORAGE_KEY);
        } catch (e) {
            console.warn('Failed to remove persisted auth', e);
        }
    }

    static getUser(): any | null {
        if (typeof window === 'undefined') return null;
        const userStr = localStorage.getItem(this.USER_KEY);
        try {
            return userStr ? JSON.parse(userStr) : null;
        } catch {
            return null;
        }
    }
}
