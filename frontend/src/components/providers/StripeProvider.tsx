"use client";

import { Elements } from "@stripe/react-stripe-js";
import { loadStripe } from "@stripe/stripe-js/pure";
import type { ReactNode } from "react";
import { useCallback, useEffect, useState } from "react";
import type { Stripe, StripeElementsOptions } from "@stripe/stripe-js";

import { Button } from "@/components/ui/button";
import { PaymentFormSkeleton } from "@/components/billing/PaymentFormSkeleton";
import { StripeErrorBoundary } from "@/components/billing/StripeErrorBoundary";
import { useTheme } from "@/hooks/use-theme";

const stripePublishableKey = process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY;

interface StripeProviderProps {
  children: ReactNode;
  options?: StripeElementsOptions;
}

/**
 * Stripe Provider Component
 * Wraps children with Stripe Elements context for payment forms
 */
export function StripeProvider({ children, options }: Readonly<StripeProviderProps>) {
  const { isDarkMode } = useTheme();
  const [stripePromise, setStripePromise] = useState<Promise<Stripe | null> | null>(null);
  const [stripeLoadError, setStripeLoadError] = useState<Error | null>(null);
  const [isStripeReady, setIsStripeReady] = useState(false);
  const [retryCount, setRetryCount] = useState(0);

  useEffect(() => {
    let isMounted = true;
    setStripePromise(null);
    setStripeLoadError(null);
    setIsStripeReady(false);

    if (!stripePublishableKey) {
      setStripeLoadError(new Error("Stripe publishable key is not configured"));
      return () => {
        isMounted = false;
      };
    }

    try {
      // Resolve failures to null before passing the promise to Elements. The
      // Stripe React adapter attaches a success-only handler to this promise,
      // so passing the raw rejected promise creates an unhandled rejection.
      const safeStripePromise = loadStripe(stripePublishableKey).catch((error: unknown) => {
        const normalizedError = error instanceof Error
          ? error
          : new Error("Failed to load Stripe.js");

        if (isMounted) {
          setStripeLoadError(normalizedError);
        }
        return null;
      });

      setStripePromise(safeStripePromise);
      void safeStripePromise.then((stripe) => {
        if (!isMounted) {
          return;
        }

        if (stripe) {
          setIsStripeReady(true);
        } else {
          setStripeLoadError(new Error("Stripe.js is not available"));
        }
      });
    } catch (error) {
      if (isMounted) {
        setStripeLoadError(
          error instanceof Error ? error : new Error("Failed to load Stripe.js"),
        );
      }
    }

    return () => {
      isMounted = false;
    };
  }, [retryCount]);

  const handleRetry = useCallback(() => {
    setStripePromise(null);
    setStripeLoadError(null);
    setIsStripeReady(false);
    setRetryCount((count) => count + 1);
  }, []);

  if (stripeLoadError) {
    return (
      <div
        role="alert"
        className="space-y-4 rounded-lg border border-destructive/50 bg-destructive/5 p-4"
      >
        <p className="text-sm text-muted-foreground">
          Payment form unavailable. Stripe.js could not be loaded. Check your connection and try again.
        </p>
        <Button type="button" variant="outline" size="sm" onClick={handleRetry}>
          Try again
        </Button>
      </div>
    );
  }

  if (!stripePromise || !isStripeReady) {
    return <PaymentFormSkeleton />;
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
    <StripeErrorBoundary onRetry={handleRetry}>
      <Elements
        stripe={stripePromise}
        options={{ ...defaultOptions, ...options }}
      >
        {children}
      </Elements>
    </StripeErrorBoundary>
  );
}

export default StripeProvider;
