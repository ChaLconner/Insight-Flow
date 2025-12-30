"use client";

import type { ErrorInfo, ReactNode } from "react";
import React, { Component } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { AlertTriangle, RefreshCw, CreditCard } from "lucide-react";

interface Props {
  children: ReactNode;
  fallbackMessage?: string;
  onRetry?: () => void;
  showRetry?: boolean;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

/**
 * Error Boundary specifically designed for Stripe Elements.
 * Catches errors from Stripe.js initialization, card element rendering,
 * and payment form submissions.
 * 
 * Usage:
 * <StripeErrorBoundary onRetry={() => refetch()}>
 *   <Elements stripe={stripePromise}>
 *     <PaymentForm />
 *   </Elements>
 * </StripeErrorBoundary>
 */
export class StripeErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    this.setState({ errorInfo });
    
    // Log to console in development
    if (process.env.NODE_ENV === "development") {
      console.error("StripeErrorBoundary caught an error:", error);
      console.error("Component stack:", errorInfo.componentStack);
    }
    
    // Log to error tracking service in production
    // e.g., Sentry.captureException(error, { extra: { componentStack: errorInfo.componentStack } });
  }

  handleRetry = (): void => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    this.props.onRetry?.();
  };

  isStripeError(error: Error): boolean {
    const stripeErrorPatterns = [
      /stripe/i,
      /payment/i,
      /card/i,
      /SetupIntent/i,
      /PaymentIntent/i,
      /confirmCardSetup/i,
      /Elements/i,
    ];
    
    return stripeErrorPatterns.some(pattern => 
      pattern.test(error.message) || pattern.test(error.name)
    );
  }

  getErrorMessage(): string {
    const { error } = this.state;
    const { fallbackMessage } = this.props;
    
    if (fallbackMessage) {return fallbackMessage;}
    
    if (error) {
      // Check for specific Stripe errors
      if (error.message.includes("network")) {
        return "Network error. Please check your connection and try again.";
      }
      if (error.message.includes("timeout")) {
        return "The request timed out. Please try again.";
      }
      if (error.message.includes("invalid")) {
        return "Invalid card information. Please check and try again.";
      }
      if (error.message.includes("declined")) {
        return "Your card was declined. Please try a different card.";
      }
      if (this.isStripeError(error)) {
        return "Payment processing error. Please try again or use a different payment method.";
      }
    }
    
    return "Something went wrong with the payment form. Please try again.";
  }

  render(): ReactNode {
    if (this.state.hasError) {
      const showRetry = this.props.showRetry ?? true;
      
      return (
        <Card className="border-destructive/50 bg-destructive/5">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-destructive text-lg">
              <AlertTriangle className="h-5 w-5" />
              Payment Error
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-start gap-3">
              <div className="p-2 rounded-lg bg-destructive/10">
                <CreditCard className="h-5 w-5 text-destructive" />
              </div>
              <div className="flex-1">
                <p className="text-sm text-muted-foreground">
                  {this.getErrorMessage()}
                </p>
                {process.env.NODE_ENV === "development" && this.state.error && (
                  <details className="mt-2">
                    <summary className="text-xs text-muted-foreground cursor-pointer hover:text-foreground">
                      Technical details
                    </summary>
                    <pre className="mt-2 p-2 bg-background rounded text-xs overflow-auto max-h-32 border border-border">
                      {this.state.error.message}
                      {this.state.errorInfo?.componentStack}
                    </pre>
                  </details>
                )}
              </div>
            </div>
            
            {showRetry && (
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={this.handleRetry}
                  className="gap-2"
                >
                  <RefreshCw className="h-4 w-4" />
                  Try Again
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      );
    }

    return this.props.children;
  }
}

/**
 * HOC to wrap any component with Stripe error boundary
 */
export function withStripeErrorBoundary<P extends object>(
  WrappedComponent: React.ComponentType<P>,
  fallbackMessage?: string
) {
  return function WithStripeErrorBoundary(props: P) {
    return (
      <StripeErrorBoundary fallbackMessage={fallbackMessage}>
        <WrappedComponent {...props} />
      </StripeErrorBoundary>
    );
  };
}

export default StripeErrorBoundary;
