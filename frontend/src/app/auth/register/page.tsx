"use client";

import { useGoogleLogin } from "@react-oauth/google";
import { useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiClient } from "@/lib/api-client";
import { authActions } from "@/stores/auth-actions";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { registerSchema, type RegisterSchema } from "@/lib/validations/auth";
import { getErrorMessage } from "@/lib/error-utils";
import { GoogleIcon } from "@/components/auth/GoogleIcon";
import { PasswordVisibilityButton } from "@/components/auth/PasswordVisibilityButton";
import { getSocialSignupRedirect } from "@/lib/auth-redirect";

import {
  Mail,
  Lock,

  Github,
  ArrowRight,
  Loader2,
  Layers,
} from "lucide-react";
import { toast } from "sonner";

// Wrapper component to handle Suspense for useSearchParams
export default function RegisterPage() {
  return (
    <Suspense fallback={<RegisterPageSkeleton />}>
      <RegisterPageContent />
    </Suspense>
  );
}

// Loading skeleton for the register page
function RegisterPageSkeleton() {
  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="animate-pulse">
          <div className="h-12 w-12 bg-muted rounded-xl mx-auto mb-4" />
          <div className="h-8 bg-muted rounded w-3/4 mx-auto mb-2" />
          <div className="h-4 bg-muted rounded w-1/2 mx-auto mb-8" />
          <div className="h-96 bg-muted rounded-lg" />
        </div>
      </div>
    </div>
  );
}

function RegisterPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const plan = searchParams.get("plan");

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

  const handleGitHubSignupClick = () => {
    if (isLoading) {return;}
    try { sessionStorage.setItem("auth_oauth_started", "1"); } catch { /* ignore */ }
    window.location.href = "/auth/github/start";
  };



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
        plan: plan ?? undefined, // Send plan if it exists
      };

      await apiClient.post("/auth/register", backendUserData);

      // Registration successful - redirect to login
      toast.success("Account created successfully", {
        description: "Please check your email to verify your account before logging in.",
      });
      
      const isPaidPlan = plan && plan !== "free";
      const redirectPath = isPaidPlan 
        ? `/auth/login?callbackUrl=${encodeURIComponent("/settings?tab=billing")}`
        : "/auth/login";

      router.push(redirectPath);
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
        const isPaidPlan = plan && plan !== "free";
        const redirectUrl = getSocialSignupRedirect(user?.role, Boolean(isPaidPlan));

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
    onNonOAuthError: (error) => {
      console.warn("Google login popup error:", error.type);
      setIsLoading(false);

      if (error.type === "popup_closed") {
        return;
      }

      const description =
        error.type === "popup_failed_to_open"
          ? "Google popup was blocked. Please allow popups and try again."
          : "Google login could not be completed. Please try again.";

      setApiError(description);
      toast.error("Google login failed", {
        description,
      });
    },
    flow: "implicit",
  });



  return (
    <div className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden">
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
                <GoogleIcon />
                Continue with Google
              </Button>
              <Button
                variant="outline"
                className="w-full bg-slate-900 hover:bg-slate-800 border-slate-700 text-white transition-all hover:scale-[1.02]"
                onClick={handleGitHubSignupClick}
                disabled={isLoading}
                title="Sign up with GitHub"
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
                  <PasswordVisibilityButton
                    isVisible={showPassword}
                    onToggle={() => setShowPassword(!showPassword)}
                    disabled={isLoading}
                  />
                </div>

                <p className="text-xs text-muted-foreground mt-2">
                  At least 8 characters
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
                  <PasswordVisibilityButton
                    isVisible={showConfirmPassword}
                    onToggle={() => setShowConfirmPassword(!showConfirmPassword)}
                    disabled={isLoading}
                  />
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
                className="w-full bg-white hover:bg-gray-200 text-black font-bold py-2.5 transition-all hover:scale-[1.02]"
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
