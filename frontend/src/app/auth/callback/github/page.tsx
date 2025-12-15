"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { API_CONFIG } from "@/lib/constants";
import { authActions } from "@/stores/auth-actions";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";

export default function GitHubCallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(true);

  useEffect(() => {
    const handleCallback = async () => {
      const code = searchParams.get("code");
      const errorParam = searchParams.get("error");
      const errorDescription = searchParams.get("error_description");

      if (errorParam) {
        setError(errorDescription || errorParam);
        setIsProcessing(false);
        toast.error("GitHub login failed", { description: errorDescription || errorParam });
        return;
      }

      if (!code) {
        setError("No authorization code received from GitHub");
        setIsProcessing(false);
        toast.error("GitHub login failed", { description: "No authorization code received" });
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
          throw new Error(errorData?.detail || "GitHub authentication failed");
        }

        const data = await response.json();
        console.log("✅ GitHub login successful");

        // Use authActions to handle login
        await authActions.loginWithResponse(data);

        const user = data.user;
        let redirectUrl = "/dashboard";

        if (user?.role) {
          switch (user.role) {
            case "admin":
              redirectUrl = "/dashboard";
              break;
            case "manager":
              redirectUrl = "/projects";
              break;
            case "member":
            case "user":
              redirectUrl = "/projects?tab=tasks";
              break;
            case "viewer":
              redirectUrl = "/projects";
              break;
            default:
              redirectUrl = "/dashboard";
          }
        }

        toast.success("Login successful!", {
          description: `Welcome${user?.name ? `, ${user.name}` : ""}!`,
        });

        // Redirect to dashboard
        window.location.href = redirectUrl;
      } catch (err) {
        console.error("❌ GitHub callback error:", err);
        const errorMessage = err instanceof Error ? err.message : "GitHub authentication failed";
        setError(errorMessage);
        toast.error("GitHub login failed", { description: errorMessage });
      } finally {
        setIsProcessing(false);
      }
    };

    handleCallback();
  }, [searchParams, router]);

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-zinc-900 via-zinc-800 to-indigo-900 flex items-center justify-center p-4">
        <div className="text-center">
          <div className="mx-auto h-12 w-12 rounded-xl bg-red-600 flex items-center justify-center mb-4">
            <span className="text-2xl">✕</span>
          </div>
          <h1 className="text-2xl font-bold text-white mb-2">Authentication Failed</h1>
          <p className="text-zinc-400 mb-6">{error}</p>
          <button
            onClick={() => router.push("/auth/login")}
            className="px-6 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition-colors"
          >
            Back to Login
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-zinc-900 via-zinc-800 to-indigo-900 flex items-center justify-center p-4">
      <div className="text-center">
        <div className="mx-auto h-12 w-12 rounded-xl bg-indigo-600 flex items-center justify-center mb-4">
          <Loader2 className="h-6 w-6 text-white animate-spin" />
        </div>
        <h1 className="text-2xl font-bold text-white mb-2">Signing in with GitHub</h1>
        <p className="text-zinc-400">Please wait while we complete your authentication...</p>
      </div>
    </div>
  );
}
