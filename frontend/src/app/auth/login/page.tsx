"use client";
import { useGoogleLogin } from "@react-oauth/google";
import { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AnimatedBackground, FloatingShapes } from "@/components/ui/animated-background";
import { authActions } from "@/stores/auth-actions";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { loginSchema, type LoginSchema } from "@/lib/validations/auth";
import { apiClient } from "@/lib/api-client";
import { GoogleIcon } from "@/components/auth/GoogleIcon";
import { PasswordVisibilityButton } from "@/components/auth/PasswordVisibilityButton";
import { getAuthRedirectUrl } from "@/lib/auth-redirect";
import { createOAuthState, getGitHubRedirectUri } from "@/lib/social-auth";

import {
  Mail,
  Lock,
  Github,
  ArrowRight,
  Loader2,
  Layers,
} from "lucide-react";
import { toast } from "sonner";
import { getErrorMessage } from "@/lib/error-utils";

const GITHUB_OAUTH_STATE_KEY = "github_oauth_state";
const GITHUB_OAUTH_REDIRECT_KEY = "github_oauth_redirect";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const requestedRedirect =
    searchParams.get("callbackUrl") ?? searchParams.get("redirect");
  
  const form = useForm<LoginSchema>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: "",
      password: "",
      rememberMe: false,
    },
  });

  useEffect(() => {
    const message = searchParams.get("message");
    if (message) {
      toast.info(message);
    }
  }, [searchParams]);

  const onSubmit = async (values: LoginSchema) => {
    setIsLoading(true);
    try {
      // Call backend API
      const response = await apiClient.post("/auth/login", {
        email: values.email,
        password: values.password,
        remember_me: values.rememberMe,
      });

      const data = response.data;
      
      // Use authActions to properly handle login (this will show the toast)
      await authActions.loginWithResponse(data);

      const user = data.user;
      const redirectUrl = getAuthRedirectUrl({
        role: user?.role,
        callbackUrl: requestedRedirect,
      });

      router.replace(redirectUrl);

    } catch (error) {
      console.error("❌ Login error:", error);
      const errorMessage = getErrorMessage(error);
      toast.error("Login failed", { description: errorMessage });
      // Reset password field on error
      form.setValue("password", "");
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoogleLogin = useGoogleLogin({
    onSuccess: async (tokenResponse) => {
      try {
        setIsLoading(true);

        const response = await apiClient.post("/auth/google", {
          access_token: tokenResponse.access_token,
        });

        const data = response.data;



        await authActions.loginWithResponse(data);

        const user = data.user;
        const redirectUrl = getAuthRedirectUrl({
          role: user?.role,
          callbackUrl: requestedRedirect,
        });

        router.replace(redirectUrl);
      } catch (error) {
        console.error("❌ Google login error:", error);
        toast.error("Google login failed", {
          description: getErrorMessage(error),
        });
      } finally {
        setIsLoading(false);
      }
    },
    onError: () => {
      toast.error("Google login failed");
      setIsLoading(false);
    },
    onNonOAuthError: (error) => {
      console.warn("Google login popup error:", error.type);
      setIsLoading(false);

      if (error.type === "popup_closed") {
        return;
      }

      toast.error("Google login failed", {
        description:
          error.type === "popup_failed_to_open"
            ? "Google popup was blocked. Please allow popups and try again."
            : "Google login could not be completed. Please try again.",
      });
    },
    flow: "implicit",
  });



  return (
    <div className="w-full max-w-md relative z-20">
      {/* Logo */}
      <div className="text-center mb-8">
        <div className="mx-auto h-12 w-12 rounded-xl bg-primary flex items-center justify-center mb-4 shadow-lg shadow-primary/25">
          <Layers className="h-7 w-7 text-primary-foreground" />
        </div>
        <h1 className="text-2xl font-bold text-white mb-2">Welcome back</h1>
        <p className="text-gray-200">Sign in to your Insight Flow account</p>
      </div>

      <Card className="bg-slate-950 shadow-2xl border-slate-800 ring-1 ring-slate-800">
        <CardHeader className="space-y-1 pb-6">
          <CardTitle className="text-xl text-white text-center">
            Sign in
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Social Login */}
          <div className="space-y-3">
            <Button
              variant="outline"
              className="w-full bg-slate-900 hover:bg-slate-800 border-slate-700 text-white transition-all hover:scale-[1.02]"
              onClick={() => handleGoogleLogin()}
              disabled={isLoading || !process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID}
              title={
                !process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID
                  ? "Google Client ID is missing"
                  : "Sign in with Google"
              }
            >
              <GoogleIcon />
              Continue with Google
            </Button>
            <Button
              variant="outline"
              className="w-full bg-slate-900 hover:bg-slate-800 border-slate-700 text-white transition-all hover:scale-[1.02]"
              onClick={() => {
                const clientId = process.env.NEXT_PUBLIC_GITHUB_CLIENT_ID;
                if (!clientId) {
                  toast.error("GitHub login not configured");
                  return;
                }
                const redirectUri = encodeURIComponent(
                  getGitHubRedirectUri(),
                );
                const state = createOAuthState();
                window.sessionStorage.setItem(GITHUB_OAUTH_STATE_KEY, state);
                if (requestedRedirect) {
                  window.sessionStorage.setItem(
                    GITHUB_OAUTH_REDIRECT_KEY,
                    requestedRedirect,
                  );
                } else {
                  window.sessionStorage.removeItem(GITHUB_OAUTH_REDIRECT_KEY);
                }
                const scope = "read:user user:email";
                window.location.href = `https://github.com/login/oauth/authorize?client_id=${clientId}&redirect_uri=${redirectUri}&scope=${scope}&state=${encodeURIComponent(state)}`;
              }}
              disabled={isLoading}
              title="Sign in with GitHub"
            >
              <Github className="h-4 w-4 mr-3" />
              Continue with GitHub
            </Button>
          </div>

          {/* Divider */}
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-border" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-transparent px-2 text-gray-200">
                Or continue with
              </span>
            </div>
          </div>

          {/* Login Form */}
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email" className="text-white">
                Email
              </Label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" aria-hidden="true" />
                <Input
                  id="email"
                  type="email"
                  placeholder="Enter your email"
                  autoComplete="email"
                  autoFocus
                  className={`pl-10 bg-slate-900 border-slate-700 text-white placeholder:text-gray-200 focus:border-primary focus:bg-slate-800 transition-all ${
                    form.formState.errors.email ? "border-red-500" : ""
                  }`}
                  disabled={isLoading}
                  {...form.register("email")}
                  aria-invalid={!!form.formState.errors.email}
                />
              </div>
              {form.formState.errors.email && (
                <p role="alert" className="text-sm text-red-400">
                  {form.formState.errors.email.message}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="password" className="text-white">
                Password
              </Label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" aria-hidden="true" />
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  placeholder="Enter your password"
                  autoComplete="current-password"
                  className={`pl-10 pr-10 bg-slate-900 border-slate-700 text-white placeholder:text-gray-200 focus:border-primary focus:bg-slate-800 transition-all ${
                    form.formState.errors.password ? "border-red-500" : ""
                  }`}
                  disabled={isLoading}
                  {...form.register("password")}
                  aria-invalid={!!form.formState.errors.password}
                />
                <PasswordVisibilityButton
                  isVisible={showPassword}
                  onToggle={() => setShowPassword(!showPassword)}
                  disabled={isLoading}
                />
              </div>
              {form.formState.errors.password && (
                <p role="alert" className="text-sm text-red-400">
                  {form.formState.errors.password.message}
                </p>
              )}
            </div>

            <div className="flex items-center justify-between">
              <label className="flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  className="rounded border-border bg-background text-primary focus:ring-primary focus:ring-offset-0"
                  {...form.register("rememberMe")}
                />
                <span className="ml-2 text-sm text-gray-300">
                  Remember me
                </span>
              </label>
              <Link
                href="/auth/forgot-password"
                className="text-sm text-white hover:text-gray-200 transition-colors underline decoration-gray-500 hover:decoration-white"
              >
                Forgot password?
              </Link>
            </div>

            <Button
              type="submit"
              className="w-full bg-white hover:bg-gray-200 text-black font-bold py-2.5 transition-all hover:scale-[1.02]"
              disabled={isLoading}
            >
              {isLoading ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <>
                  Sign in
                  <ArrowRight className="h-4 w-4 ml-2" />
                </>
              )}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Footer */}
      <p className="text-center text-sm text-white mt-6">
        Don't have an account?{" "}
        <Link
          href="/auth/register"
          className="text-white hover:text-gray-200 font-medium transition-colors underline"
        >
          Sign up
        </Link>
      </p>
    </div>
  );
}

export default function LoginPage() {
  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4 relative overflow-hidden">
      {/* Animated Background Components */}
      <AnimatedBackground />
      <FloatingShapes />

      <Suspense fallback={
        <div className="z-20 p-8 rounded-xl bg-white/5 backdrop-blur-md">
           <Loader2 className="h-8 w-8 text-primary animate-spin" />
        </div>
      }>
        <LoginForm />
      </Suspense>
    </div>
  );
}
