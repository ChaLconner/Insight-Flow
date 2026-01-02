"use client";

import { useGoogleLogin } from "@react-oauth/google";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  AnimatedBackground,
  FloatingShapes,
} from "@/components/ui/animated-background";
import { apiClient } from "@/lib/api-client";
import { authActions } from "@/stores/auth-actions";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { registerSchema, type RegisterSchema } from "@/lib/validations/auth";
import { getErrorMessage } from "@/lib/error-utils";

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

export default function RegisterPage() {
  const router = useRouter();
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [apiError, setApiError] = useState<string>("");

  const form = useForm<RegisterSchema>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      fullName: "",
      email: "",
      password: "",
      confirmPassword: "",
      terms: false,
    },
    mode: "onChange", // Enable live validation
  });



  const onSubmit = async (values: RegisterSchema) => {
    setIsLoading(true);
    setApiError("");

    try {
      // Generate unique username from email
      const emailPrefix = values.email.split('@')[0].replace(/[^a-zA-Z0-9]/g, '');
      const uniqueSuffix = Math.floor(1000 + Math.random() * 9000);
      const username = `${emailPrefix}${uniqueSuffix}`;

      // Transform frontend data to match backend UserCreate schema
      const backendUserData = {
        email: values.email.trim(),
        username: username,
        name: values.fullName.trim(),
        password: values.password,
      };

      await apiClient.post("/auth/register", backendUserData);

      // Registration successful - redirect to login
      toast.success("Account created successfully", {
        description: "Please sign in with your new account.",
      });
      router.push("/auth/login");
    } catch (error: unknown) {
      console.error("Registration error:", error);

      // Handle API errors
      let errorMessage = "";
      // Use getErrorMessage helper if possible, but keeping local logic for now as backup or reusing helper
      errorMessage = getErrorMessage(error);

      setApiError(errorMessage);
      toast.error("Registration failed", { description: errorMessage });
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoogleLogin = useGoogleLogin({
    onSuccess: async (tokenResponse) => {
      try {
        setIsLoading(true);
        setApiError("");

        // Call backend API with Google token using apiClient
        const response = await apiClient.post("/auth/google", {
          access_token: tokenResponse.access_token,
        });

        const data = response.data;

        await authActions.loginWithResponse(data);

        const user = data.user;
        let redirectUrl = "/dashboard";
        if (user?.role === "member" || user?.role === "user") {
          redirectUrl = "/projects?tab=tasks";
        } else if (user?.role === "manager" || user?.role === "viewer") {
          redirectUrl = "/projects";
        }

        router.push(redirectUrl);
      } catch (error) {
        console.error("❌ Google login error:", error);
        const msg = getErrorMessage(error);
        setApiError(msg);
        toast.error("Google login failed", {
          description: msg,
        });
      } finally {
        setIsLoading(false);
      }
    },
    onError: () => {
      console.error("❌ Google login failed");
      setApiError("Google login failed. Please try again.");
      setIsLoading(false);
      toast.error("Google login failed");
    },
    flow: "implicit",
  });



  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4 relative overflow-hidden">
      {/* Animated Background Components */}
      <AnimatedBackground />
      <FloatingShapes />

      <div className="w-full max-w-md relative z-20">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="mx-auto h-12 w-12 rounded-xl bg-primary flex items-center justify-center mb-4 shadow-lg shadow-primary/25">
            <Layers className="h-7 w-7 text-primary-foreground" />
          </div>
          <h1 className="text-2xl font-bold text-foreground mb-2">
            Create your account
          </h1>
          <p className="text-muted-foreground">
            Join Insight Flow and start managing projects
          </p>
        </div>

        <Card className="bg-slate-950 shadow-2xl border-slate-800 ring-1 ring-slate-800">
          <CardHeader className="space-y-1 pb-6">
            <CardTitle className="text-xl text-foreground text-center">
              Sign up
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* API Error Display */}
            {apiError && (
              <div role="alert" className="bg-red-500/10 border border-red-500/20 rounded-md p-3">
                <p className="text-sm text-red-400">{apiError}</p>
              </div>
            )}

            {/* Social Login */}
            <div className="space-y-3">
              <Button
                variant="outline"
                className="w-full bg-slate-900 hover:bg-slate-800 border-slate-700 text-white transition-all hover:scale-[1.02]"
                onClick={() => handleGoogleLogin()}
                disabled={
                  isLoading || !process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID
                }
                title={
                  !process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID
                    ? "Google Client ID is missing"
                    : "Sign up with Google"
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
                className="w-full bg-slate-900 hover:bg-slate-800 border-slate-700 text-white transition-all hover:scale-[1.02]"
                onClick={() => {
                  const clientId = process.env.NEXT_PUBLIC_GITHUB_CLIENT_ID;
                  if (!clientId) {
                    toast.error("GitHub signup not configured");
                    return;
                  }
                  const redirectUri = encodeURIComponent(
                    `${window.location.origin}/auth/callback/github`,
                  );
                  const scope = "read:user user:email";
                  window.location.href = `https://github.com/login/oauth/authorize?client_id=${clientId}&redirect_uri=${redirectUri}&scope=${scope}`;
                }}
                disabled={isLoading}
                title={
                  !process.env.NEXT_PUBLIC_GITHUB_CLIENT_ID
                    ? "GitHub Client ID is missing"
                    : "Sign up with GitHub"
                }
              >
                <Github className="h-4 w-4 mr-3" />
                Continue with GitHub
              </Button>
            </div>

            {/* Divider */}
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-slate-800" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-transparent px-2 text-gray-200">
                  Or continue with
                </span>
              </div>
            </div>

            {/* Register Form */}
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
              {/* Full Name */}
              <div className="space-y-2">
                <Label htmlFor="fullName" className="text-white">
                  Full Name
                </Label>
                <Input
                  id="fullName"
                  placeholder="John Doe"
                  autoComplete="name"
                  autoFocus
                  className={`bg-slate-900 border-slate-700 text-white placeholder:text-gray-200 focus:border-primary focus:bg-slate-800 transition-all ${
                    form.formState.errors.fullName ? "border-red-500" : ""
                  }`}
                  disabled={isLoading}
                  {...form.register("fullName")}
                  aria-invalid={!!form.formState.errors.fullName}
                />
                {form.formState.errors.fullName && (
                  <p role="alert" className="text-xs text-red-400">{form.formState.errors.fullName.message}</p>
                )}
              </div>

              {/* Email */}
              <div className="space-y-2">
                <Label htmlFor="email" className="text-white">
                  Email
                </Label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" aria-hidden="true" />
                  <Input
                    id="email"
                    type="email"
                    placeholder="john@example.com"
                    autoComplete="email"
                    className={`pl-10 bg-slate-900 border-slate-700 text-white placeholder:text-gray-200 focus:border-primary focus:bg-slate-800 transition-all ${
                      form.formState.errors.email ? "border-red-500" : ""
                    }`}
                    disabled={isLoading}
                    {...form.register("email")}
                    aria-invalid={!!form.formState.errors.email}
                  />
                </div>
                {form.formState.errors.email && (
                  <p role="alert" className="text-xs text-red-400">{form.formState.errors.email.message}</p>
                )}
              </div>



              {/* Password */}
              <div className="space-y-2">
                <Label htmlFor="password" className="text-white">
                  Password
                </Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" aria-hidden="true" />
                  <Input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    placeholder="Create a strong password"
                    className={`pl-10 pr-10 bg-slate-900 border-slate-700 text-white placeholder:text-gray-200 focus:border-primary focus:bg-slate-800 transition-all ${
                      form.formState.errors.password ? "border-red-500" : ""
                    }`}
                    disabled={isLoading}
                    {...form.register("password")}
                    aria-invalid={!!form.formState.errors.password}
                    autoComplete="new-password"
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

                <p className="text-xs text-muted-foreground mt-2">
                  Use 8 or more characters with a mix of letters, numbers & symbols
                </p>

                {form.formState.errors.password && (
                  <p role="alert" className="text-xs text-red-400">{form.formState.errors.password.message}</p>
                )}
              </div>

              {/* Confirm Password */}
              <div className="space-y-2">
                <Label htmlFor="confirmPassword" className="text-white">
                  Confirm Password
                </Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" aria-hidden="true" />
                  <Input
                    id="confirmPassword"
                    type={showConfirmPassword ? "text" : "password"}
                    placeholder="Confirm your password"
                    className={`pl-10 pr-10 bg-slate-900 border-slate-700 text-white placeholder:text-gray-200 focus:border-primary focus:bg-slate-800 transition-all ${
                      form.formState.errors.confirmPassword ? "border-red-500" : ""
                    }`}
                    disabled={isLoading}
                    {...form.register("confirmPassword")}
                    aria-invalid={!!form.formState.errors.confirmPassword}
                    autoComplete="new-password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute right-3 top-1/2 transform -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    disabled={isLoading}
                    title={showConfirmPassword ? "Hide password" : "Show password"}
                    aria-label={showConfirmPassword ? "Hide password" : "Show password"}
                  >
                    {showConfirmPassword ? (
                      <EyeOff className="h-4 w-4" />
                    ) : (
                      <Eye className="h-4 w-4" />
                    )}
                  </button>
                </div>
                {form.formState.errors.confirmPassword && (
                  <p role="alert" className="text-xs text-red-400">
                    {form.formState.errors.confirmPassword.message}
                  </p>
                )}
              </div>

              {/* Terms and Conditions */}
              <div className="space-y-2">
                <label className="flex items-start gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    className="mt-1 rounded border-border bg-background/50 text-indigo-600 focus:ring-indigo-500 focus:ring-offset-0"
                    disabled={isLoading}
                    {...form.register("terms")}
                  />
                  <span className="text-sm text-muted-foreground">
                    I agree to{" "}
                    <Link
                      href="/terms"
                      className="text-blue-300 hover:text-blue-200"
                    >
                      Terms of Service
                    </Link>{" "}
                    and{" "}
                    <Link
                      href="/privacy"
                      className="text-blue-300 hover:text-blue-200"
                    >
                      Privacy Policy
                    </Link>
                  </span>
                </label>
                {form.formState.errors.terms && (
                  <p role="alert" className="text-xs text-red-400">{form.formState.errors.terms.message}</p>
                )}
              </div>

              <Button
                type="submit"
                className="w-full bg-white hover:bg-gray-200 text-black font-bold py-2.5"
                disabled={isLoading || !form.formState.isValid}
              >
                {isLoading ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <>
                    Create Account
                    <ArrowRight className="h-4 w-4 ml-2" />
                  </>
                )}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Footer */}
        <p className="text-center text-sm text-muted-foreground mt-6">
          Already have an account?{" "}
          <Link
            href="/auth/login"
            className="text-white hover:text-gray-200 font-medium transition-colors underline"
          >
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
