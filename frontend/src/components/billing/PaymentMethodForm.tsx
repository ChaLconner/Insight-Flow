"use client";

import { useState } from "react";
import {
  PaymentElement,
  useStripe,
  useElements,
} from "@stripe/react-stripe-js";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2, Lock, ShieldCheck } from "lucide-react";
import { apiClient } from "@/lib/api-client";

interface PaymentMethodFormProps {
  clientSecret: string;
  onSuccess: () => void;
  onCancel: () => void;
  defaultName?: string;
}

export function PaymentMethodForm({
  onSuccess,
  onCancel,
}: PaymentMethodFormProps) {
  const stripe = useStripe();
  const elements = useElements();
  
  const [isLoading, setIsLoading] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cardName, setCardName] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!stripe || !elements) {
      return;
    }

    if (!cardName.trim()) {
      setError("Cardholder name is required");
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const { error: setupError, setupIntent } = await stripe.confirmSetup({
        elements,
        confirmParams: {
          return_url: window.location.href,
          payment_method_data: {
            billing_details: {
              name: cardName,
              address: { country: "TH" },
            },
          },
        },
        redirect: "if_required",
      });

      if (setupError) {
        setError(setupError.message ?? "An error occurred");
        setIsLoading(false);
        return;
      }

      if (setupIntent?.status === "succeeded") {
        const response = await apiClient.post("/payment/methods", {
          payment_method_id: setupIntent.payment_method,
          set_as_default: true,
          billing_name: cardName,
        });

        if (response.status !== 201) {
          throw new Error("Failed to save payment method");
        }

        setIsComplete(true);
        setTimeout(() => {
          onSuccess();
        }, 1500);
      } else {
        setError(`Setup failed with status: ${setupIntent?.status || 'unknown'}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "An unexpected error occurred");
    } finally {
      setIsLoading(false);
    }
  };

  if (isComplete) {
    return (
      <div className="flex flex-col items-center justify-center py-12 space-y-4 animate-in fade-in zoom-in duration-300">
        <div className="h-20 w-20 rounded-full bg-[#5552D9]/10 flex items-center justify-center ring-1 ring-[#5552D9]/20">
          <ShieldCheck className="h-10 w-10 text-[#5552D9]" />
        </div>
        <div className="text-center space-y-1">
          <h3 className="text-xl font-semibold text-foreground">
            Payment Method Added
          </h3>
          <p className="text-sm text-muted-foreground">
            Your card has been securely saved.
          </p>
        </div>
      </div>
    );
  }

  // Custom styling for Payment Element
  const paymentElementOptions = {
    layout: "tabs" as const,
    fields: {
      billingDetails: {
        address: { country: "never" as const }
      }
    },
    terms: {
      card: 'never' as const,
    },
    appearance: {
      theme: 'stripe' as const,
      variables: {
        colorPrimary: '#5552D9',
        colorBackground: '#ffffff',
        colorText: '#1f2937',
        dangerColor: '#df1b41',
        fontFamily: 'Inter, system-ui, sans-serif',
        spacingUnit: '4px',
        borderRadius: '12px',
      },
      rules: {
        '.Input': {
          borderColor: '#e5e7eb',
          paddingTop: '12px',
          paddingBottom: '12px',
          boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
        },
        '.Input:focus': {
          borderColor: '#5552D9',
          boxShadow: '0 0 0 1px #5552D9',
        },
        '.Label': {
          fontWeight: '500',
          fontSize: '0.875rem',
          color: '#374151',
          marginBottom: '6px',
        }
      }
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="space-y-5">
        {/* Stripe Elements Group */}
        <div className="space-y-4">
            <PaymentElement options={paymentElementOptions} />

            {/* Card Name Input - Matched to Design */}
            <div className="space-y-1.5">
              <Label htmlFor="cardName" className="block text-sm font-medium text-text-main-light dark:text-text-main-dark mb-1.5" style={{ fontFamily: 'Inter, sans-serif' }}>
                Card Name
              </Label>
              <Input
                id="cardName"
                name="cardName"
                type="text"
                value={cardName}
                onChange={(e) => setCardName(e.target.value)}
                className="block w-full rounded-md border-gray-300 dark:border-slate-600 bg-white text-gray-900 focus:border-[#5552D9] focus:ring-[#5552D9] sm:text-base py-6 px-3 placeholder-gray-400 transition-all font-sans"
                placeholder="Name on card"
                autoComplete="cc-name"
                required
              />
            </div>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="p-3 rounded-xl bg-red-50 text-red-600 border border-red-100 text-sm font-medium animate-in slide-in-from-top-2 flex items-center gap-2">
            <div className="h-1.5 w-1.5 rounded-full bg-red-600" />
            {error}
        </div>
      )}

      {/* Action Buttons - Matched to Design */}
      <div className="grid grid-cols-2 gap-4 pt-4">
        <Button
          type="button"
          onClick={onCancel}
          disabled={isLoading}
          className="w-full inline-flex justify-center items-center px-4 py-6 border border-gray-300 dark:border-slate-600 shadow-sm text-sm font-medium rounded-xl text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-800 hover:bg-gray-50 dark:hover:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#5552D9] transition-colors"
        >
          Cancel
        </Button>
        <Button
          type="submit"
          disabled={!stripe || isLoading}
          className="w-full inline-flex justify-center items-center px-4 py-6 border border-transparent shadow-lg shadow-indigo-500/30 text-sm font-medium rounded-xl text-white bg-[#5552D9] hover:bg-[#4340b5] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#5552D9] transition-all"
        >
          {isLoading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Processing
            </>
          ) : (
            "Save Card"
          )}
        </Button>
      </div>

      <div className="flex items-center justify-center space-x-2 pt-2 opacity-60">
        <Lock className="h-3 w-3 text-green-600 dark:text-green-400" />
        <span className="text-[10px] font-semibold tracking-wider text-slate-500 dark:text-slate-400 uppercase">
            Secure Payment Processing
        </span>
      </div>
    </form>
  );
}

export default PaymentMethodForm;
