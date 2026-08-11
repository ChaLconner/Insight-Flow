import React from "react";
import { act, render, renderHook, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { SubscriptionPlan, type PlanInfo } from "@/types";

const apiClientMock = {
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  delete: vi.fn(),
};

vi.mock("@/lib/api-client", () => ({
  apiClient: apiClientMock,
}));

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
}));

vi.mock("@/stores/auth-store", () => ({
  useAuthStore: vi.fn((selector?: (state: unknown) => unknown) => {
    const state = {
      isAuthenticated: true,
      isInitialized: true,
      user: {
        id: "user-1",
        name: "Jane Doe",
      },
    };

    return typeof selector === "function" ? selector(state) : state;
  }),
}));

function createDeferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });

  return { promise, resolve, reject };
}

describe("billing bottleneck regression", () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    apiClientMock.get.mockReset();
    apiClientMock.post.mockReset();
    apiClientMock.put.mockReset();
    apiClientMock.delete.mockReset();

    const paymentModule = await import("@/hooks/usePayment");
    paymentModule.__clearPaymentCachesForTests();

    const billingModule = await import("@/hooks/useBillingData");
    billingModule.__clearBillingDataCacheForTests();

    const paymentHistoryModule = await import("@/app/settings/components/payment-history-settings");
    paymentHistoryModule.__clearPaymentHistoryCacheForTests();
  });

  it("dedupes concurrent payment method fetches", async () => {
    const deferred = createDeferred<{
      data: {
        payment_methods: Array<Record<string, unknown>>;
        total: number;
      };
    }>();
    apiClientMock.get.mockReturnValue(deferred.promise);

    const paymentModule = await import("@/hooks/usePayment");
    const firstHook = renderHook(() => paymentModule.usePaymentMethods());
    const secondHook = renderHook(() => paymentModule.usePaymentMethods());

    let firstFetchPromise!: Promise<void>;
    let secondFetchPromise!: Promise<void>;
    await act(async () => {
      firstFetchPromise = firstHook.result.current.fetchMethods();
      secondFetchPromise = secondHook.result.current.fetchMethods();
    });

    expect(apiClientMock.get).toHaveBeenCalledTimes(1);

    await act(async () => {
      deferred.resolve({
        data: {
          payment_methods: [
            {
              id: "pm_1",
              card_brand: "visa",
              card_last4: "4242",
              card_exp_month: 1,
              card_exp_year: 2030,
              is_default: true,
            },
          ],
          total: 1,
        },
      });

      await Promise.all([firstFetchPromise, secondFetchPromise]);
    });
  });

  it("bypasses stale in-flight payment methods request when force refresh is used", async () => {
    const firstDeferred = createDeferred<{
      data: {
        payment_methods: Array<Record<string, unknown>>;
        total: number;
      };
    }>();
    const secondDeferred = createDeferred<{
      data: {
        payment_methods: Array<Record<string, unknown>>;
        total: number;
      };
    }>();

    apiClientMock.get.mockReturnValueOnce(firstDeferred.promise).mockReturnValueOnce(secondDeferred.promise);

    const paymentModule = await import("@/hooks/usePayment");
    const hook = renderHook(() => paymentModule.usePaymentMethods());

    let firstFetchPromise!: Promise<void>;
    await act(async () => {
      firstFetchPromise = hook.result.current.fetchMethods();
    });

    let secondFetchPromise!: Promise<void>;
    await act(async () => {
      secondFetchPromise = hook.result.current.fetchMethods({ force: true });
    });

    expect(apiClientMock.get).toHaveBeenCalledTimes(2);

    await act(async () => {
      secondDeferred.resolve({
        data: {
          payment_methods: [
            {
              id: "pm_new",
              card_brand: "mastercard",
              card_last4: "5555",
              card_exp_month: 2,
              card_exp_year: 2031,
              is_default: true,
            },
          ],
          total: 1,
        },
      });
      await secondFetchPromise;
    });

    await act(async () => {
      firstDeferred.resolve({
        data: {
          payment_methods: [
            {
              id: "pm_old",
              card_brand: "visa",
              card_last4: "4242",
              card_exp_month: 1,
              card_exp_year: 2030,
              is_default: true,
            },
          ],
          total: 1,
        },
      });
      await firstFetchPromise;
    });

    expect(hook.result.current.methods[0]?.id).toBe("pm_new");
  });

  it("dedupes concurrent billing data mounts", async () => {
    const freePlan: PlanInfo = {
      plan: SubscriptionPlan.FREE,
      name: "Free",
      price_monthly: 0,
      price_yearly: 0,
      currency: "usd",
      features: [],
      project_limit: 2,
      member_limit: 3,
      original_price: null,
      discount_percent: 0,
      color: "text-gray-500",
      badge: null,
      badge_color: null,
      is_limited_offer: false,
    };
    const plansDeferred = createDeferred<{ data: { plans: PlanInfo[] } }>();
    const usageDeferred = createDeferred<{ data: { projects_used: number; seats_used: number } }>();

    apiClientMock.get.mockReturnValueOnce(plansDeferred.promise).mockReturnValueOnce(usageDeferred.promise);

    const billingModule = await import("@/hooks/useBillingData");
    await act(async () => {
      renderHook(() => billingModule.useBillingData());
      renderHook(() => billingModule.useBillingData());
    });

    await waitFor(() => expect(apiClientMock.get).toHaveBeenCalledTimes(2));

    await act(async () => {
      plansDeferred.resolve({
        data: {
          plans: [freePlan],
        },
      });
      usageDeferred.resolve({
        data: {
          projects_used: 1,
          seats_used: 2,
        },
      });

      await Promise.all([plansDeferred.promise, usageDeferred.promise]);
    });
  });

  it("bypasses stale in-flight billing data request when force refresh is used", async () => {
    const freePlan: PlanInfo = {
      plan: SubscriptionPlan.FREE,
      name: "Free",
      price_monthly: 0,
      price_yearly: 0,
      currency: "usd",
      features: [],
      project_limit: 2,
      member_limit: 3,
      original_price: null,
      discount_percent: 0,
      color: "text-gray-500",
      badge: null,
      badge_color: null,
      is_limited_offer: false,
    };
    const proPlan: PlanInfo = {
      ...freePlan,
      plan: SubscriptionPlan.PRO,
      name: "Pro",
      price_monthly: 19,
      price_yearly: 190,
      project_limit: 50,
      member_limit: 20,
      color: "text-blue-500",
    };

    const firstPlansDeferred = createDeferred<{ data: { plans: PlanInfo[] } }>();
    const firstUsageDeferred = createDeferred<{ data: { projects_used: number; seats_used: number } }>();
    const secondPlansDeferred = createDeferred<{ data: { plans: PlanInfo[] } }>();
    const secondUsageDeferred = createDeferred<{ data: { projects_used: number; seats_used: number } }>();

    apiClientMock.get
      .mockReturnValueOnce(firstPlansDeferred.promise)
      .mockReturnValueOnce(firstUsageDeferred.promise)
      .mockReturnValueOnce(secondPlansDeferred.promise)
      .mockReturnValueOnce(secondUsageDeferred.promise);

    const billingModule = await import("@/hooks/useBillingData");
    const hook = renderHook(() => billingModule.useBillingData());

    let forceRefreshPromise!: Promise<void>;
    await waitFor(() => expect(apiClientMock.get).toHaveBeenCalledTimes(2));

    await act(async () => {
      forceRefreshPromise = hook.result.current.refresh({ force: true });
    });

    expect(apiClientMock.get).toHaveBeenCalledTimes(4);

    await act(async () => {
      secondPlansDeferred.resolve({
        data: {
          plans: [proPlan],
        },
      });
      secondUsageDeferred.resolve({
        data: {
          projects_used: 4,
          seats_used: 7,
        },
      });
      await forceRefreshPromise;
    });

    firstPlansDeferred.resolve({
      data: {
        plans: [freePlan],
      },
    });
    firstUsageDeferred.resolve({
      data: {
        projects_used: 1,
        seats_used: 2,
      },
    });

    await waitFor(() => expect(hook.result.current.plans.pro?.name).toBe("Pro"));
    expect(hook.result.current.usageStats.projects).toBe(4);
  });

  it("dedupes payment history fetches under React strict mode", async () => {
    const statsDeferred = createDeferred<{
      data: {
        total_spent: number;
        total_payments: number;
        successful_payments: number;
        failed_payments: number;
        pending_payments: number;
        refunded_payments: number;
        currency: string;
      };
    }>();
    const historyDeferred = createDeferred<{
      data: {
        payments: never[];
        total: number;
      };
    }>();

    apiClientMock.get.mockReturnValueOnce(statsDeferred.promise).mockReturnValueOnce(historyDeferred.promise);

    const { PaymentHistorySettings } = await import("@/app/settings/components/payment-history-settings");
    await act(async () => {
      render(
        <React.StrictMode>
          <PaymentHistorySettings />
        </React.StrictMode>,
      );
    });

    await waitFor(() => expect(apiClientMock.get).toHaveBeenCalledTimes(2));

    await act(async () => {
      statsDeferred.resolve({
        data: {
          total_spent: 100,
          total_payments: 1,
          successful_payments: 1,
          failed_payments: 0,
          pending_payments: 0,
          refunded_payments: 0,
          currency: "usd",
        },
      });
      historyDeferred.resolve({
        data: {
          payments: [],
          total: 0,
        },
      });

      await Promise.all([statsDeferred.promise, historyDeferred.promise]);
    });

    await waitFor(() => expect(apiClientMock.get).toHaveBeenCalledTimes(2));
  });

  it("renders payment history status variants and document actions", async () => {
    apiClientMock.get
      .mockResolvedValueOnce({
        data: {
          total_spent: 300,
          total_payments: 3,
          successful_payments: 1,
          failed_payments: 1,
          pending_payments: 1,
          refunded_payments: 0,
          currency: "usd",
        },
      })
      .mockResolvedValueOnce({
        data: {
          payments: [
            {
              id: "payment-succeeded",
              amount: 100,
              currency: "usd",
              status: "succeeded",
              created_at: "2026-01-01T00:00:00Z",
              description: "Successful payment",
              invoice_url: "https://example.com/invoice",
              receipt_url: null,
            },
            {
              id: "payment-failed",
              amount: 100,
              currency: "usd",
              status: "failed",
              created_at: "2026-01-02T00:00:00Z",
              description: null,
              invoice_url: null,
              receipt_url: "https://example.com/receipt",
            },
            {
              id: "payment-pending",
              amount: 100,
              currency: "usd",
              status: "pending",
              created_at: "2026-01-03T00:00:00Z",
              description: null,
              invoice_url: null,
              receipt_url: null,
            },
          ],
          total: 3,
        },
      });

    const { PaymentHistorySettings } = await import(
      "@/app/settings/components/payment-history-settings"
    );
    render(<PaymentHistorySettings />);

    await waitFor(() => expect(screen.getByText("succeeded")).toBeInTheDocument());
    expect(screen.getByText("failed")).toBeInTheDocument();
    expect(screen.getByText("pending")).toBeInTheDocument();
    expect(screen.getByText("Invoice")).toBeInTheDocument();
    expect(screen.getByText("Receipt")).toBeInTheDocument();
  });
});
