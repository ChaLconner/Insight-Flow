"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { API_CONFIG } from "@/lib/constants";
import { getAuthRedirectUrl } from "@/lib/auth-redirect";
import { authActions } from "@/stores/auth-actions";
import { getGitHubRedirectUri } from "@/lib/social-auth";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";

const GITHUB_OAUTH_STATE_KEY = "github_oauth_state";
const GITHUB_OAUTH_REDIRECT_KEY = "github_oauth_redirect";
const GITHUB_OAUTH_COOKIE_PATH = "/auth/callback/github";

function getCookie(name: string): string | null {
  const cookie = document.cookie
    .split("; ")
    .find((item) => item.startsWith(`${name}=`));

  if (!cookie) {
    return null;
  }

  return decodeURIComponent(cookie.slice(name.length + 1));
}

function deleteCookie(name: string) {
  document.cookie = `${name}=; Max-Age=0; path=${GITHUB_OAUTH_COOKIE_PATH}; SameSite=Lax`;
}

function GitHubCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const handleCallback = async () => {
      // Clear the OAuth navigation marker – we completed the flow
      // (or at least reached the callback). This prevents a stale flag
      // from causing an unnecessary reload on future auth page visits.
      try { sessionStorage.removeItem("auth_oauth_started"); } catch {}

      const code = searchParams.get("code");
      const state = searchParams.get("state");
      const errorParam = searchParams.get("error");
      const errorDescription = searchParams.get("error_description");

      if (errorParam) {
        setError(errorDescription ?? errorParam);
        toast.error("GitHub login failed", {
          description: errorDescription ?? errorParam,
        });
        return;
      }

      if (!code) {
        setError("No authorization code received from GitHub");
        toast.error("GitHub login failed", {
          description: "No authorization code received",
        });
        return;
      }

      if (typeof window !== "undefined") {
        const expectedState =
          window.sessionStorage.getItem(GITHUB_OAUTH_STATE_KEY) ??
          getCookie(GITHUB_OAUTH_STATE_KEY);
        if (!state || !expectedState || state !== expectedState) {
          setError("Invalid GitHub OAuth state");
          toast.error("GitHub login failed", {
            description: "Invalid OAuth state. Please try again.",
          });
          window.sessionStorage.removeItem(GITHUB_OAUTH_STATE_KEY);
          window.sessionStorage.removeItem(GITHUB_OAUTH_REDIRECT_KEY);
          deleteCookie(GITHUB_OAUTH_STATE_KEY);
          deleteCookie(GITHUB_OAUTH_REDIRECT_KEY);
          return;
        }
        window.sessionStorage.removeItem(GITHUB_OAUTH_STATE_KEY);
        deleteCookie(GITHUB_OAUTH_STATE_KEY);
      }

      try {
        // Send the code to our backend
        const response = await fetch(`${API_CONFIG.BASE_URL}/auth/github`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          credentials: "include",
          body: JSON.stringify({
            code,
            redirect_uri: getGitHubRedirectUri(),
          }),
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData?.detail ?? "GitHub authentication failed");
        }

        const data = await response.json();


        // Use authActions to handle login
        await authActions.loginWithResponse(data);

        const user = data.user;
        const oauthRedirect =
          typeof window !== "undefined"
            ? (window.sessionStorage.getItem(GITHUB_OAUTH_REDIRECT_KEY) ??
              getCookie(GITHUB_OAUTH_REDIRECT_KEY))
            : null;
        if (typeof window !== "undefined") {
          window.sessionStorage.removeItem(GITHUB_OAUTH_REDIRECT_KEY);
          deleteCookie(GITHUB_OAUTH_REDIRECT_KEY);
        }
        const redirectUrl = getAuthRedirectUrl({
          role: user?.role,
          callbackUrl: oauthRedirect,
        });

        toast.success("Login successful!", {
          description: `Welcome${user?.name ? `, ${user.name}` : ""}!`,
        });

        router.replace(redirectUrl);
      } catch (err) {
        console.error("❌ GitHub callback error:", err);
        const errorMessage =
          err instanceof Error ? err.message : "GitHub authentication failed";
        setError(errorMessage);
        toast.error("GitHub login failed", { description: errorMessage });
      }
    };

    handleCallback();
  }, [searchParams, router]);

  if (error) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
        <div className="text-center">
          <div className="mx-auto h-12 w-12 rounded-xl bg-destructive/10 flex items-center justify-center mb-4">
            <span className="text-2xl text-destructive">✕</span>
          </div>
          <h1 className="text-2xl font-bold text-foreground mb-2">
            Authentication Failed
          </h1>
          <p className="text-muted-foreground mb-6">{error}</p>
          <button
            onClick={() => router.push("/auth/login")}
            className="px-6 py-2 bg-primary hover:bg-primary/90 text-primary-foreground rounded-lg transition-colors"
          >
            Back to Login
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="text-center">
        <div className="mx-auto h-12 w-12 rounded-xl bg-primary/10 flex items-center justify-center mb-4">
          <Loader2 className="h-6 w-6 text-primary animate-spin" />
        </div>
        <h1 className="text-2xl font-bold text-foreground mb-2">
          Signing in with GitHub
        </h1>
        <p className="text-muted-foreground">
          Please wait while we complete your authentication...
        </p>
      </div>
    </div>
  );
}

export default function GitHubCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-background flex items-center justify-center p-4">
          <Loader2 className="h-6 w-6 text-primary animate-spin" />
        </div>
      }
    >
      <GitHubCallbackContent />
    </Suspense>
  );
}
