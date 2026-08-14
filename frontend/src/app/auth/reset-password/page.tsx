"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { apiClient } from "@/lib/api-client";
import { toast } from "sonner";
import { getErrorMessage } from "@/lib/error-utils";
import { Loader2 } from "lucide-react";
import { AuthStatusIcon } from "@/components/auth/AuthStatusIcon";

function ResetPasswordForm() {
  const [token, setToken] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [error, setError] = useState("");
  const [tokenError, setTokenError] = useState("");
  /* const router = useRouter(); */ // unused
  const searchParams = useSearchParams();

  useEffect(() => {
    const tokenFromUrl = searchParams.get("token");

    if (!tokenFromUrl) {
      setTokenError("Invalid reset link. Please request a new password reset.");
    } else {
      setToken(tokenFromUrl);
      // Validate token immediately
      validateToken(tokenFromUrl);
    }
  }, [searchParams]);

  const validateToken = async (token: string) => {
    try {
      const response = await apiClient.post("/auth/validate-reset-token", {
        token,
      });

      if (!response.data.valid) {
        setTokenError(
          response.data.message ?? "Invalid or expired reset token.",
        );
      }
    } catch (err) {
      console.error("Token validation error:", err);
      // If validation endpoint doesn't exist, continue anyway
      const axiosError = err as { response?: { status?: number } };
      if (axiosError.response?.status !== 404) {
        setTokenError("Failed to validate reset token. Please try again.");
      }
    }
  };

  const validateForm = () => {
    if (!newPassword || !confirmPassword) {
      setError("Please fill in all fields");
      return false;
    }

    if (newPassword.length < 8) {
      setError("Password must be at least 8 characters long");
      return false;
    }

    if (newPassword !== confirmPassword) {
      setError("Passwords do not match");
      return false;
    }

    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    setIsLoading(true);
    setError("");

    try {
      const response = await apiClient.post("/auth/reset-password", {
        token,
        new_password: newPassword,
      });

      if (response.data.success) {
        setIsSuccess(true);
        toast.success("Password reset successful", {
          description: "You can now login with your new password",
        });
      } else {
        setError("Failed to reset password. Please try again.");
        toast.error("Failed to reset password");
      }
    } catch (err) {
      console.error("Reset password error:", err);
      const errorMsg = getErrorMessage(err);
      setError(errorMsg);
      toast.error("Failed to reset password", { description: errorMsg });
    } finally {
      setIsLoading(false);
    }
  };

  if (tokenError) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-transparent py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-md w-full space-y-8">
          <Card>
            <CardContent className="pt-6">
              <div className="text-center space-y-4">
                <div className="text-red-600">
                  <AuthStatusIcon tone="error" />
                </div>
                <div>
                  <h3 className="text-lg font-medium text-gray-900">
                    Invalid Reset Link
                  </h3>
                  <p className="mt-2 text-sm text-gray-600">{tokenError}</p>
                </div>
                <div className="space-y-2">
                  <Link href="/auth/forgot-password">
                    <Button className="w-full">Request New Reset Link</Button>
                  </Link>
                  <Link href="/auth/login">
                    <Button variant="outline" className="w-full">
                      Back to Login
                    </Button>
                  </Link>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  if (isSuccess) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-transparent py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-md w-full space-y-8">
          <Card>
            <CardContent className="pt-6">
              <div className="text-center space-y-4">
                <div className="text-green-600">
                  <AuthStatusIcon tone="success" />
                </div>
                <div>
                  <h3 className="text-lg font-medium text-gray-900">
                    Password Reset Successful
                  </h3>
                  <p className="mt-2 text-sm text-gray-600">
                    Your password has been reset successfully. You can now login
                    with your new password.
                  </p>
                </div>
                <Link href="/auth/login">
                  <Button className="w-full">Go to Login</Button>
                </Link>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-transparent py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <h2 className="mt-6 text-3xl font-extrabold text-white">
            Reset your password
          </h2>
          <p className="mt-2 text-sm text-gray-200">
            Enter your new password below.
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>New Password</CardTitle>
            <CardDescription>
              Choose a strong password with at least 8 characters.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="new_password">New Password</Label>
                <Input
                  id="new_password"
                  name="new_password"
                  type="password"
                  autoComplete="new-password"
                  required
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Enter new password"
                  disabled={isLoading}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="confirm_password">Confirm Password</Label>
                <Input
                  id="confirm_password"
                  name="confirm_password"
                  type="password"
                  autoComplete="new-password"
                  required
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Confirm new password"
                  disabled={isLoading}
                />
              </div>

              {error && <div className="text-red-600 text-sm">{error}</div>}

              <Button type="submit" className="w-full" disabled={isLoading}>
                {isLoading ? "Resetting..." : "Reset Password"}
              </Button>
            </form>
          </CardContent>
        </Card>

        <div className="text-center">
          <Link
            href="/auth/login"
            className="text-blue-600 hover:text-blue-500 text-sm"
          >
            Back to login
          </Link>
        </div>
      </div>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-transparent">
          <Loader2 className="h-8 w-8 text-primary animate-spin" />
        </div>
      }
    >
      <ResetPasswordForm />
    </Suspense>
  );
}
