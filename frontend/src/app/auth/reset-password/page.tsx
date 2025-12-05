"use client";

import { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api-client";

export default function ResetPasswordPage() {
  const [token, setToken] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [error, setError] = useState("");
  const [tokenError, setTokenError] = useState("");
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const tokenFromUrl = searchParams.get("token");
    console.log("Reset password page loaded, token from URL:", tokenFromUrl);

    if (!tokenFromUrl) {
      console.error("No token found in URL");
      setTokenError("Invalid reset link. Please request a new password reset.");
    } else {
      setToken(tokenFromUrl);
      // Validate token immediately
      validateToken(tokenFromUrl);
    }
  }, [searchParams]);

  const validateToken = async (token: string) => {
    try {
      console.log("Validating reset token...");
      const response = await apiClient.post("/auth/validate-reset-token", { token });
      console.log("Token validation response:", response.data);

      if (!response.data.valid) {
        setTokenError(response.data.message || "Invalid or expired reset token.");
      }
    } catch (err: any) {
      console.error("Token validation error:", err);
      // If validation endpoint doesn't exist, continue anyway
      if (err.response?.status !== 404) {
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

    console.log("Reset password form submitted");
    setIsLoading(true);
    setError("");

    try {
      const response = await apiClient.post("/auth/reset-password", {
        token,
        new_password: newPassword
      });

      console.log("Reset password response:", response.data);

      if (response.data.success) {
        setIsSuccess(true);
      } else {
        setError("Failed to reset password. Please try again.");
      }
    } catch (err: any) {
      console.error("Reset password error:", err);
      console.error("Error details:", {
        message: err.message,
        status: err.status,
        response: err.response
      });
      setError(err.response?.data?.detail || err.message || "An error occurred. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  if (tokenError) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-md w-full space-y-8">
          <Card>
            <CardContent className="pt-6">
              <div className="text-center space-y-4">
                <div className="text-red-600">
                  <svg
                    className="mx-auto h-12 w-12 text-red-500"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                </div>
                <div>
                  <h3 className="text-lg font-medium text-gray-900">
                    Invalid Reset Link
                  </h3>
                  <p className="mt-2 text-sm text-gray-600">
                    {tokenError}
                  </p>
                </div>
                <div className="space-y-2">
                  <Link href="/auth/forgot-password">
                    <Button className="w-full">
                      Request New Reset Link
                    </Button>
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
      <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-md w-full space-y-8">
          <Card>
            <CardContent className="pt-6">
              <div className="text-center space-y-4">
                <div className="text-green-600">
                  <svg
                    className="mx-auto h-12 w-12 text-green-500"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                </div>
                <div>
                  <h3 className="text-lg font-medium text-gray-900">
                    Password Reset Successful
                  </h3>
                  <p className="mt-2 text-sm text-gray-600">
                    Your password has been reset successfully. You can now login with your new password.
                  </p>
                </div>
                <Link href="/auth/login">
                  <Button className="w-full">
                    Go to Login
                  </Button>
                </Link>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <h2 className="mt-6 text-3xl font-extrabold text-gray-900">
            Reset your password
          </h2>
          <p className="mt-2 text-sm text-gray-600">
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

              {error && (
                <div className="text-red-600 text-sm">{error}</div>
              )}

              <Button
                type="submit"
                className="w-full"
                disabled={isLoading}
              >
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