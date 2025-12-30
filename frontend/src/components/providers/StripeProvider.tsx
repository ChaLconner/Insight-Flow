"use client";

import { Elements } from "@stripe/react-stripe-js";
import { loadStripe } from "@stripe/stripe-js";
import type { ReactNode } from "react";
import type { StripeElementsOptions } from "@stripe/stripe-js";

import { useTheme } from "@/hooks/use-theme";

// Initialize Stripe with publishable key
const stripePromise = process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY
  ? loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY)
  : null;

interface StripeProviderProps {
  children: ReactNode;
  options?: StripeElementsOptions;
}

/**
 * Stripe Provider Component
 * Wraps children with Stripe Elements context for payment forms
 */
export function StripeProvider({ children, options }: StripeProviderProps) {
  const { isDarkMode } = useTheme();

  if (!stripePromise) {
    // If Stripe is not configured, render children without Stripe context
    // This is expected in development without Stripe keys
    return <>{children}</>;
  }

  const defaultOptions = {
    appearance: {
      theme: isDarkMode ? ("night" as const) : ("stripe" as const),
      variables: {
        colorPrimary: "#6366f1",
        colorBackground: isDarkMode ? "#020817" : "#ffffff", // Matches shadcn card background
        colorText: isDarkMode ? "#f9fafb" : "#1f2937",
        colorDanger: "#ef4444",
        fontFamily: "Inter, system-ui, sans-serif",
        borderRadius: "8px",
      },
    },
  };

  return (
    <Elements
      stripe={stripePromise}
      options={{ ...defaultOptions, ...options }}
    >
      {children}
    </Elements>
  );
}

export default StripeProvider;
