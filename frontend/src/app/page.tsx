"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/auth-store";

/**
 * Root page - Redirects to dashboard if authenticated
 * This page acts as an entry point and handles the initial routing
 */
export default function Home() {
  // This component will only render if middleware lets it through (which it shouldn't for '/')
  // or if we're loading initially before hydration (though middleware handles the redirect)
  return (
    <div className="min-h-screen bg-black flex items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
      </div>
    </div>
  );
}