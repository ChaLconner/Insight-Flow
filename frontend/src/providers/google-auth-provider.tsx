"use client";

import { GoogleOAuthProvider } from "@react-oauth/google";
import type { ReactNode } from "react";

interface GoogleAuthProviderProps {
  children: ReactNode;
}

export function GoogleAuthProvider({ children }: Readonly<GoogleAuthProviderProps>) {
  const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;

  if (!clientId) {
    console.warn("Google Client ID is not set in environment variables");
  }

  return (
    <GoogleOAuthProvider clientId={clientId ?? "missing-google-client-id"}>
      {children}
    </GoogleOAuthProvider>
  );
}
