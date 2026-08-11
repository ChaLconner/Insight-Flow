"use client";

import { useState } from "react";

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
import { AuthStatusIcon } from "@/components/auth/AuthStatusIcon";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [error, setError] = useState("");
  /* const router = useRouter(); */ // unused

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    setIsLoading(true);
    setError("");

    try {
      const response = await apiClient.post("/auth/forgot-password", { email });

      if (response.data.success) {
        setIsSubmitted(true);
        toast.success("Reset link sent", {
          description: "Check your email for instructions",
        });
      } else {
        setError("Failed to send reset email. Please try again.");
      }
    } catch (err: unknown) {
      console.error("Forgot password error:", err);
      const errorMsg = getErrorMessage(err);
      setError(errorMsg);
      toast.error("Failed to send reset link", { description: errorMsg });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-transparent py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <h2 className="mt-6 text-3xl font-extrabold text-white">
            Forgot your password?
          </h2>
          <p className="mt-2 text-sm text-gray-200">
            Enter your email address and we'll send you a link to reset your
            password.
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Reset Password</CardTitle>
            <CardDescription>
              We'll email you instructions to reset your password.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {!isSubmitted ? (
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="email">Email address</Label>
                  <Input
                    id="email"
                    name="email"
                    type="email"
                    autoComplete="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="Enter your email"
                    disabled={isLoading}
                  />
                </div>

                {error && <div className="text-red-600 text-sm">{error}</div>}

                <Button type="submit" className="w-full" disabled={isLoading}>
                  {isLoading ? "Sending..." : "Send Reset Link"}
                </Button>
              </form>
            ) : (
              <div className="text-center space-y-4">
                <div className="text-green-600">
                  <AuthStatusIcon tone="success" />
                </div>
                <div>
                  <h3 className="text-lg font-medium text-gray-900">
                    Check your email
                  </h3>
                  <p className="mt-2 text-sm text-gray-600">
                    We've sent a password reset link to {email}. The link will
                    expire in 1 hour.
                  </p>
                </div>
                <div className="text-sm text-gray-600">
                  Didn't receive the email? Check your spam folder or{" "}
                  <button type="button"
                    onClick={() => setIsSubmitted(false)}
                    className="text-blue-600 hover:text-blue-500"
                  >
                    try again
                  </button>
                </div>
              </div>
            )}
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
