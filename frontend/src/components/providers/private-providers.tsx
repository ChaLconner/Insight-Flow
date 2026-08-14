"use client";

import { Toaster } from "sonner";
import { QueryProvider } from "@/providers/query-provider";
import { AuthInitializer } from "@/components/providers/auth-initializer";
import { ThemeProvider } from "@/components/providers/theme-provider";

export function PrivateProviders({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <QueryProvider>
      <ThemeProvider>
        {children}
        <Toaster
          position="bottom-right"
          richColors
          theme="system"
          className="font-sans"
          toastOptions={{
            classNames: {
              title: "text-sm font-semibold",
              description: "text-xs text-muted-foreground",
              actionButton: "bg-primary text-primary-foreground",
              cancelButton: "bg-muted text-muted-foreground",
            },
            style: {
              background: "rgba(23, 23, 23, 0.8)",
              backdropFilter: "blur(12px)",
              border: "1px solid rgba(255, 255, 255, 0.1)",
              color: "white",
            },
          }}
        />
        <AuthInitializer />
      </ThemeProvider>
    </QueryProvider>
  );
}
