"use client";

import { useState, useCallback } from "react";
import { toast } from "sonner";
import type {
  PaymentMethod,
  SetupIntentResponse,
  Subscription,
  PlanInfo,
  PlansListResponse,
} from "@/types";

import { apiClient } from "@/lib/api-client";

// ============================================================================
// usePaymentMethods Hook
// ============================================================================

interface UsePaymentMethodsReturn {
  methods: PaymentMethod[];
  isLoading: boolean;
  error: string | null;
  fetchMethods: () => Promise<void>;
  setDefault: (id: string) => Promise<void>;
  deleteMethod: (id: string) => Promise<void>;
}

export function usePaymentMethods(): UsePaymentMethodsReturn {
  const [methods, setMethods] = useState<PaymentMethod[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Transform snake_case API response to camelCase
  const transformPaymentMethod = (pm: Record<string, unknown>): PaymentMethod => ({
    id: pm.id as string,
    cardBrand: (pm.card_brand as string) ?? "unknown",
    cardLast4: (pm.card_last4 as string) ?? "****",
    cardExpMonth: (pm.card_exp_month as number) ?? 1,
    cardExpYear: (pm.card_exp_year as number) ?? 2030,
    cardFunding: pm.card_funding as string | undefined,
    cardCountry: pm.card_country as string | undefined,
    isDefault: (pm.is_default as boolean) ?? false,
    isActive: (pm.is_active as boolean) ?? true,
    billingName: pm.billing_name as string | undefined,
    billingEmail: pm.billing_email as string | undefined,
    billingPhone: pm.billing_phone as string | undefined,
    billingAddressLine1: pm.billing_address_line1 as string | undefined,
    billingAddressLine2: pm.billing_address_line2 as string | undefined,
    billingCity: pm.billing_city as string | undefined,
    billingState: pm.billing_state as string | undefined,
    billingPostalCode: pm.billing_postal_code as string | undefined,
    billingCountry: pm.billing_country as string | undefined,
    createdAt: (pm.created_at as string) ?? new Date().toISOString(),
  });

  const fetchMethods = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const { data } = await apiClient.get<{ payment_methods: Record<string, unknown>[]; total: number }>(
        "/payment/methods"
      );
      
      // Transform each payment method from snake_case to camelCase
      const transformed = data.payment_methods.map(transformPaymentMethod);
      setMethods(transformed);
    } catch (err: unknown) {
      if (err instanceof Error && (err as { response?: { status: number } }).response?.status === 503) {
        setMethods([]);
        return;
      }
      const message = err instanceof Error ? err.message : "An error occurred";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const setDefault = useCallback(
    async (id: string) => {
      setIsLoading(true);
      try {
        await apiClient.put(`/payment/methods/${id}/default`);
        await fetchMethods();
        toast.success("Default card updated", {
          description: "Your default payment card has been changed.",
        });
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : "An error occurred";
        setError(message);
        toast.error("Failed to update default card", {
          description: message,
        });
      } finally {
        setIsLoading(false);
      }
    },
    [fetchMethods]
  );

  const deleteMethod = useCallback(
    async (id: string) => {
      setIsLoading(true);
      try {
        await apiClient.delete(`/payment/methods/${id}`);
        await fetchMethods();
        toast.success("Card removed", {
          description: "Your payment card has been deleted.",
        });
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : "Failed to delete";
        setError(message);
        toast.error("Failed to remove card", {
          description: message,
        });
      } finally {
        setIsLoading(false);
      }
    },
    [fetchMethods]
  );

  return { methods, isLoading, error, fetchMethods, setDefault, deleteMethod };
}

// ============================================================================
// useSetupIntent Hook
// ============================================================================

interface UseSetupIntentReturn {
  setupIntent: SetupIntentResponse | null;
  isLoading: boolean;
  error: string | null;
  createSetupIntent: () => Promise<SetupIntentResponse | null>;
  reset: () => void;
  prefetch: () => Promise<void>;
  isPrefetched: boolean;
}

export function useSetupIntent(): UseSetupIntentReturn {
  const [setupIntent, setSetupIntent] = useState<SetupIntentResponse | null>(
    null
  );
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isPrefetched, setIsPrefetched] = useState(false);

  // Track the active fetch promise to prevent duplicate requests (race conditions)
  const [fetchPromise, setFetchPromise] = useState<Promise<SetupIntentResponse> | null>(null);

  const createSetupIntent = useCallback(async () => {
    // If already prefetched, return cached result immediately
    if (isPrefetched && setupIntent) {
      return setupIntent;
    }
    
    // If a fetch is already in progress, wait for it
    if (fetchPromise) {
      try {
        return await fetchPromise;
      } catch (_err) {
        // If the pending fetch fails, we'll try again below
      }
    }
    
    setIsLoading(true);
    setError(null);
    
    // Create new promise
    const promise = apiClient.post<SetupIntentResponse>("/payment/setup-intent")
      .then(({ data }) => {
        setSetupIntent(data);
        setIsPrefetched(true);
        setFetchPromise(null); // Clear promise on success
        return data;
      });

    setFetchPromise(promise);

    try {
      const data = await promise;
      return data;
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "An error occurred";
      setError(message);
      setFetchPromise(null); // Clear promise on error
      return null;
    } finally {
      setIsLoading(false);
    }
  }, [isPrefetched, setupIntent, fetchPromise]);

  // Prefetch setup intent in background
  const prefetch = useCallback(async () => {
    if (isPrefetched || (setupIntent != null) || (fetchPromise != null)) {return;} // Don't fetch if already have data or fetching
    
    const promise = apiClient.post<SetupIntentResponse>("/payment/setup-intent")
      .then(({ data }) => {
        setSetupIntent(data);
        setIsPrefetched(true);
        setFetchPromise(null);
        return data;
      })
      .catch((err) => {
        // Prefetch failures are expected - silently ignore
        setFetchPromise(null);
        throw err;
      });
      
    setFetchPromise(promise);
  }, [isPrefetched, setupIntent, fetchPromise]);

  const reset = useCallback(() => {
    setSetupIntent(null);
    setError(null);
    setIsPrefetched(false);
  }, []);

  return { setupIntent, isLoading, error, createSetupIntent, reset, prefetch, isPrefetched };
}

// ============================================================================
// useSubscription Hook
// ============================================================================

interface UseSubscriptionReturn {
  subscription: Subscription | null;
  isLoading: boolean;
  error: string | null;
  fetchSubscription: () => Promise<void>;
  cancelSubscription: (immediately?: boolean) => Promise<void>;
  updateSubscription: (plan: string, paymentMethodId?: string) => Promise<void>;
  resumeSubscription: () => Promise<void>;
}

export function useSubscription(): UseSubscriptionReturn {
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Transform snake_case API response to camelCase
  const transformSubscription = (sub: Record<string, unknown>): Subscription => ({
    id: sub.id as string,
    plan: ((sub.plan as string) ?? "free") as Subscription["plan"],
    status: ((sub.status as string) ?? "active") as Subscription["status"],
    currentPeriodStart: sub.current_period_start as string | undefined,
    currentPeriodEnd: sub.current_period_end as string | undefined,
    cancelAtPeriodEnd: (sub.cancel_at_period_end as boolean) ?? false,
    priceAmount: sub.price_amount as number | undefined,
    priceCurrency: sub.price_currency as string | undefined,
    createdAt: (sub.created_at as string) ?? new Date().toISOString(),
    updatedAt: (sub.updated_at as string) ?? new Date().toISOString(),
  });

  const fetchSubscription = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const { data } = await apiClient.get<Record<string, unknown>>(
        "/payment/subscription"
      );
      setSubscription(transformSubscription(data));
    } catch (err: unknown) {
      // 404 means no subscription found, which corresponds to free plan (normal behavior)
      const errRes = err as { response?: { status: number }; status?: number };
      const status = errRes.response?.status ?? errRes.status;
      if (status === 404) {
        setSubscription(null);
        // Don't set error - 404 is expected for users without subscriptions
        return;
      }
      // Only set error for real failures, not 404s
      const message = err instanceof Error ? err.message : "An error occurred";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const updateSubscription = useCallback(
    async (plan: string, paymentMethodId?: string) => {
      setIsLoading(true);
      setError(null);
      try {
        const { data } = await apiClient.post<Record<string, unknown>>(
          "/payment/subscription",
          { plan, payment_method_id: paymentMethodId }
        );
        setSubscription(transformSubscription(data));
        toast.success("Plan updated", {
          description: `You are now on the ${plan.charAt(0).toUpperCase() + plan.slice(1)} plan.`,
        });
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : "Failed to update subscription";
        setError(message);
        toast.error("Failed to update plan", {
          description: message,
        });
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  const cancelSubscription = useCallback(
    async (immediately = false) => {
      setIsLoading(true);
      try {
        await apiClient.delete(`/payment/subscription`, {
          params: { cancel_immediately: immediately },
        });
        await fetchSubscription();
        toast.success("Subscription cancelled", {
          description: immediately 
            ? "Your subscription has been cancelled immediately."
            : "Your subscription will be cancelled at the end of the billing period.",
        });
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : "An error occurred";
        setError(message);
        toast.error("Failed to cancel subscription", {
          description: message,
        });
      } finally {
        setIsLoading(false);
      }
    },
    [fetchSubscription]
  );

  const resumeSubscription = useCallback(async () => {
    setIsLoading(true);
    try {
      await apiClient.post(`/payment/subscription/resume`);
      await fetchSubscription();
      toast.success("Subscription Resumed", {
        description: "Auto-renew has been turned back on. You will be billed at the end of the current period.",
      });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "An error occurred";
      setError(message);
      toast.error("Failed to resume subscription", {
        description: message,
      });
    } finally {
      setIsLoading(false);
    }
  }, [fetchSubscription]);

  return {
    subscription,
    isLoading,
    error,
    fetchSubscription,
    cancelSubscription,
    updateSubscription,
    resumeSubscription,
  };
}

// ============================================================================
// usePlans Hook
// ============================================================================

interface UsePlansReturn {
  plans: PlanInfo[];
  isLoading: boolean;
  error: string | null;
  fetchPlans: () => Promise<void>;
}

export function usePlans(): UsePlansReturn {
  const [plans, setPlans] = useState<PlanInfo[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchPlans = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const { data } = await apiClient.get<PlansListResponse>("/payment/plans");
      setPlans(data.plans);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "An error occurred";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  return { plans, isLoading, error, fetchPlans };
}
