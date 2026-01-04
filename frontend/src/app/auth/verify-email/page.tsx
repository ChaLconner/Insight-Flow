"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { apiClient } from "@/lib/api-client";
import { CheckCircle2, XCircle, Loader2, ArrowRight } from "lucide-react";
import { AnimatedBackground, FloatingShapes } from "@/components/ui/animated-background";

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={<VerifyEmailSkeleton />}>
      <VerifyEmailContent />
    </Suspense>
  );
}

function VerifyEmailSkeleton() {
  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="animate-pulse">
            <div className="h-64 bg-slate-900 rounded-lg border border-slate-800"></div>
        </div>
      </div>
    </div>
  );
}

function VerifyEmailContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  
  const [status, setStatus] = useState<"verifying" | "success" | "error">("verifying");
  const [message, setMessage] = useState("Verifying your email address...");

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setMessage("Invalid verification link. Token is missing.");
      return;
    }

    const verifyToken = async () => {
      try {
        await apiClient.get(`/auth/verify-email?token=${token}`);
        setStatus("success");
      } catch (error) {
        console.error("Verification error:", error);
        setStatus("error");
        setMessage("Failed to verify email. The link may be invalid or expired.");
      }
    };

    verifyToken();
  }, [token]);

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4 relative overflow-hidden">
      <AnimatedBackground />
      <FloatingShapes />
      
      <div className="w-full max-w-md relative z-20">
        <Card className="bg-slate-950 shadow-2xl border-slate-800 ring-1 ring-slate-800">
            <CardHeader className="pb-6 text-center">
                <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-slate-900 ring-1 ring-slate-700">
                    {status === "verifying" && <Loader2 className="h-8 w-8 animate-spin text-blue-500" />}
                    {status === "success" && <CheckCircle2 className="h-8 w-8 text-green-500" />}
                    {status === "error" && <XCircle className="h-8 w-8 text-red-500" />}
                </div>
                <CardTitle className="text-xl text-foreground">
                    {status === "verifying" && "Verifying Email"}
                    {status === "success" && "Email Verified"}
                    {status === "error" && "Verification Failed"}
                </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6 text-center">
                <p className="text-muted-foreground">
                    {status === "success" 
                        ? "Thank you for verifying your email. You can now access all features of Insight Flow." 
                        : message}
                </p>

                {status === "success" && (
                    <Button 
                        onClick={() => router.push("/auth/login")}
                        className="w-full bg-white hover:bg-gray-200 text-black font-bold"
                    >
                        Sign in
                        <ArrowRight className="ml-2 h-4 w-4" />
                    </Button>
                )}

                {status === "error" && (
                    <Button 
                        onClick={() => router.push("/auth/login")}
                        variant="outline"
                        className="w-full border-slate-700 text-white hover:bg-slate-800"
                    >
                        Back to Login
                    </Button>
                )}
                
                {status === "verifying" && (
                    <p className="text-xs text-slate-500">Please wait while we verify your token...</p>
                )}
            </CardContent>
        </Card>
        
        <div className="mt-8 text-center text-sm text-slate-500">
            &copy; {new Date().getFullYear()} Insight Flow. All rights reserved.
        </div>
      </div>
    </div>
  );
}
