"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { API_CONFIG } from "@/lib/constants";
import { getPostLoginRedirect } from "@/lib/auth-redirect";
import { authActions } from "@/stores/auth-actions";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";

function GitHubCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const handleCallback = async () => {
      const code = searchParams.get("code");
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

      try {
        // Send the code to our backend
        const response = await fetch(`${API_CONFIG.BASE_URL}/auth/github`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          credentials: "include",
          body: JSON.stringify({ code }),
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData?.detail ?? "GitHub authentication failed");
        }

        const data = await response.json();


        // Use authActions to handle login
        await authActions.loginWithResponse(data);

        const user = data.user;
        const redirectUrl = getPostLoginRedirect(user?.role);

        toast.success("Login successful!", {
          description: `Welcome${user?.name ? `, ${user.name}` : ""}!`,
        });

        // Redirect to dashboard
        window.location.href = redirectUrl;
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
