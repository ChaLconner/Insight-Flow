"use client";

import {
  useGoogleLogin,
  useGoogleOAuth,
  type NonOAuthError,
  type TokenResponse,
} from "@react-oauth/google";
import { Button } from "@/components/ui/button";
import { GoogleIcon } from "@/components/auth/GoogleIcon";
import { GoogleAuthProvider } from "@/providers/google-auth-provider";
import { useEffect, useRef } from "react";

export interface GoogleAuthButtonProps {
  disabled?: boolean;
  label: string;
  onError: () => void;
  onNonOAuthError: (error: NonOAuthError) => void;
  onSuccess: (tokenResponse: TokenResponse) => void | Promise<void>;
  autoStart?: boolean;
  title: string;
}

function GoogleAuthButtonContent({
  disabled = false,
  label,
  onError,
  onNonOAuthError,
  onSuccess,
  autoStart = false,
  title,
}: Readonly<GoogleAuthButtonProps>) {
  const handleGoogleLogin = useGoogleLogin({
    onSuccess,
    onError,
    onNonOAuthError,
    flow: "implicit",
  });
  const { scriptLoadedSuccessfully } = useGoogleOAuth();
  const hasStartedRef = useRef(false);

  useEffect(() => {
    if (!autoStart || !scriptLoadedSuccessfully || hasStartedRef.current) {
      return;
    }

    hasStartedRef.current = true;
    handleGoogleLogin();
  }, [autoStart, handleGoogleLogin, scriptLoadedSuccessfully]);

  return (
    <Button
      variant="outline"
      className="w-full bg-slate-900 hover:bg-slate-800 border-slate-700 text-white transition-all hover:scale-[1.02]"
      onClick={() => handleGoogleLogin()}
      disabled={disabled}
      title={title}
    >
      <GoogleIcon />
      {label}
    </Button>
  );
}

export function GoogleAuthButton(props: Readonly<GoogleAuthButtonProps>) {
  return (
    <GoogleAuthProvider>
      <GoogleAuthButtonContent {...props} />
    </GoogleAuthProvider>
  );
}
