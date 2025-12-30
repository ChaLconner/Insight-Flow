"use client";
import { useGoogleLogin } from "@react-oauth/google";
import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
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

import {
  Mail,
  Lock,
  Eye,
  EyeOff,
  Github,
  ArrowRight,
  Loader2,
  Layers,
} from "lucide-react";
import { toast } from "sonner";
import { getErrorMessage } from "@/lib/error-utils";

function LoginForm() {
  const searchParams = useSearchParams();
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  
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
      });

      const data = response.data;
      
      // Use authActions to properly handle login (this will show the toast)
      await authActions.loginWithResponse(data);

      // Construct redirect URL
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

      // Add small delay to allow state to settle
      setTimeout(() => {
        if (typeof window !== "undefined") {
          window.location.href = redirectUrl;
        }
      }, 100);

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


        toast.success(`Welcome ${data.user.name ?? "User"}!`, {
          description: `Logged in as @${data.user.username}`,
        });

        await authActions.loginWithResponse(data);

        const user = data.user;
        let redirectUrl = "/dashboard";
        if (user?.role === "member" || user?.role === "user") {
          redirectUrl = "/projects?tab=tasks";
        } else if (user?.role === "manager" || user?.role === "viewer") {
          redirectUrl = "/projects";
        }

        window.location.href = redirectUrl;
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
    flow: "implicit",
  });



  return (
    <div className="w-full max-w-md relative z-20">
      {/* Logo */}
      <div className="text-center mb-8">
        <div className="mx-auto h-12 w-12 rounded-xl bg-primary flex items-center justify-center mb-4 shadow-lg shadow-primary/25">
          <Layers className="h-7 w-7 text-primary-foreground" />
        </div>
        <h1 className="text-2xl font-bold text-foreground mb-2">Welcome back</h1>
        <p className="text-muted-foreground">Sign in to your Insight Flow account</p>
      </div>

      <Card className="bg-white/10 backdrop-blur-xl backdrop-saturate-[1.8] shadow-[0_8px_32px_0_rgba(0,0,0,0.36)] border-white/20 ring-1 ring-white/10">
        <CardHeader className="space-y-1 pb-6">
          <CardTitle className="text-xl text-foreground text-center">
            Sign in
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Social Login */}
          <div className="space-y-3">
            <Button
              variant="outline"
              className="w-full bg-white/5 hover:bg-white/10 border-white/20 text-white transition-all hover:scale-[1.02] hover:bg-white/20"
              onClick={() => handleGoogleLogin()}
              disabled={isLoading || !process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID}
              title={
                !process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID
                  ? "Google Client ID is missing"
                  : "Sign in with Google"
              }
            >
              <div className="mr-3 h-4 w-4 flex items-center justify-center">
                <svg
                  viewBox="0 0 24 24"
                  width="100%"
                  height="100%"
                  xmlns="http://www.w3.org/2000/svg"
                  aria-hidden="true"
                >
                  <g transform="matrix(1, 0, 0, 1, 27.009001, -39.238998)">
                    <path
                      fill="#4285F4"
                      d="M -3.264 51.509 C -3.264 50.719 -3.334 49.969 -3.454 49.239 L -14.754 49.239 L -14.754 53.749 L -8.284 53.749 C -8.574 55.229 -9.424 56.479 -10.684 57.329 L -10.684 60.329 L -6.824 60.329 C -4.564 58.239 -3.264 55.159 -3.264 51.509 Z"
                    />
                    <path
                      fill="#34A853"
                      d="M -14.754 63.239 C -11.514 63.239 -8.804 62.159 -6.824 60.329 L -10.684 57.329 C -11.764 58.049 -13.134 58.489 -14.754 58.489 C -17.884 58.489 -20.534 56.379 -21.484 53.529 L -25.464 53.529 L -25.464 56.619 C -23.494 60.539 -19.444 63.239 -14.754 63.239 Z"
                    />
                    <path
                      fill="#FBBC05"
                      d="M -21.484 53.529 C -21.734 52.809 -21.864 52.039 -21.864 51.239 C -21.864 50.439 -21.734 49.669 -21.484 48.949 L -21.484 45.859 L -25.464 45.859 C -26.284 47.479 -26.754 49.299 -26.754 51.239 C -26.754 53.179 -26.284 54.999 -25.464 56.619 L -21.484 53.529 Z"
                    />
                    <path
                      fill="#EA4335"
                      d="M -14.754 43.989 C -12.984 43.989 -11.404 44.599 -10.154 45.789 L -6.734 42.369 C -8.804 40.429 -11.514 39.239 -14.754 39.239 C -19.444 39.239 -23.494 41.939 -25.464 45.859 L -21.484 48.949 C -20.534 46.099 -17.884 43.989 -14.754 43.989 Z"
                    />
                  </g>
                </svg>
              </div>
              Continue with Google
            </Button>
            <Button
              variant="outline"
              className="w-full bg-white/5 hover:bg-white/10 border-white/20 text-white transition-all hover:scale-[1.02] hover:bg-white/20"
              onClick={() => {
                const clientId = process.env.NEXT_PUBLIC_GITHUB_CLIENT_ID;
                if (!clientId) {
                  toast.error("GitHub login not configured");
                  return;
                }
                const redirectUri = encodeURIComponent(
                  `${window.location.origin}/auth/callback/github`,
                );
                const scope = "read:user user:email";
                window.location.href = `https://github.com/login/oauth/authorize?client_id=${clientId}&redirect_uri=${redirectUri}&scope=${scope}`;
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
              <span className="bg-card px-2 text-muted-foreground">
                Or continue with
              </span>
            </div>
          </div>

          {/* Login Form */}
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email" className="text-foreground">
                Email
              </Label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  id="email"
                  type="email"
                  placeholder="Enter your email"
                  autoComplete="email"
                  className={`pl-10 bg-black/50 border-white/10 text-white placeholder:text-gray-400 focus:border-primary focus:bg-black/70 transition-all ${
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
              <Label htmlFor="password" className="text-foreground">
                Password
              </Label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  placeholder="Enter your password"
                  autoComplete="current-password"
                  className={`pl-10 pr-10 bg-black/50 border-white/10 text-white placeholder:text-gray-400 focus:border-primary focus:bg-black/70 transition-all ${
                    form.formState.errors.password ? "border-red-500" : ""
                  }`}
                  disabled={isLoading}
                  {...form.register("password")}
                  aria-invalid={!!form.formState.errors.password}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  disabled={isLoading}
                  title={showPassword ? "Hide password" : "Show password"}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
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
                <span className="ml-2 text-sm text-muted-foreground">
                  Remember me
                </span>
              </label>
              <Link
                href="/auth/forgot-password"
                className="text-sm text-primary hover:text-primary/80 transition-colors"
              >
                Forgot password?
              </Link>
            </div>

            <Button
              type="submit"
              className="w-full bg-primary hover:bg-primary/90 text-primary-foreground font-medium py-2.5"
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
      <p className="text-center text-sm text-muted-foreground mt-6">
        Don't have an account?{" "}
        <Link
          href="/auth/register"
          className="text-primary hover:text-primary/80 font-medium transition-colors"
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
