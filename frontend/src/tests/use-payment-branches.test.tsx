import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const toastMock = {
  success: vi.fn(),
  error: vi.fn(),
};

const apiClientMock = {
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  delete: vi.fn(),
};

vi.mock("sonner", () => ({
  toast: toastMock,
}));

vi.mock("@/lib/api-client", () => ({
  apiClient: apiClientMock,
}));

describe("usePayment branch coverage", () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    const paymentModule = await import("@/hooks/usePayment");
    paymentModule.__clearPaymentCachesForTests();
  });

  it("handles payment method 503 responses with an empty fallback", async () => {
    const unavailableError = Object.assign(new Error("service unavailable"), {
      response: { status: 503 },
    });
    apiClientMock.get.mockRejectedValueOnce(unavailableError);

    const paymentModule = await import("@/hooks/usePayment");
    const { result } = renderHook(() => paymentModule.usePaymentMethods());

    await act(async () => {
      await result.current.fetchMethods({ force: true });
    });

    expect(result.current.methods).toEqual([]);
    expect(result.current.error).toBeNull();
    expect(result.current.isLoading).toBe(false);
  });

  it("surfaces payment method update and delete errors", async () => {
    apiClientMock.put.mockRejectedValueOnce(new Error("cannot update default"));
    apiClientMock.delete.mockRejectedValueOnce(new Error("cannot delete card"));

    const paymentModule = await import("@/hooks/usePayment");
    const { result } = renderHook(() => paymentModule.usePaymentMethods());

    await act(async () => {
      await result.current.setDefault("pm_1");
    });

    expect(result.current.error).toBe("cannot update default");
    expect(toastMock.error).toHaveBeenCalledWith("Failed to update default card", {
      description: "cannot update default",
    });

    await act(async () => {
      await result.current.deleteMethod("pm_1");
    });

    expect(result.current.error).toBe("cannot delete card");
    expect(toastMock.error).toHaveBeenCalledWith("Failed to remove card", {
      description: "cannot delete card",
    });
  });

  it("prefetches and reuses setup intent results and can reset state", async () => {
    apiClientMock.post.mockResolvedValueOnce({
      data: { client_secret: "secret_123", customer_id: "cus_123" },
    });

    const paymentModule = await import("@/hooks/usePayment");
    const { result } = renderHook(() => paymentModule.useSetupIntent());

    await act(async () => {
      await result.current.prefetch();
    });

    await waitFor(() => expect(result.current.isPrefetched).toBe(true));

    let setupIntentResult: unknown;
    await act(async () => {
      setupIntentResult = await result.current.createSetupIntent();
    });

    expect(setupIntentResult).toEqual({
      client_secret: "secret_123",
      customer_id: "cus_123",
    });
    expect(apiClientMock.post).toHaveBeenCalledTimes(1);

    act(() => {
      result.current.reset();
    });

    expect(result.current.setupIntent).toBeNull();
    expect(result.current.isPrefetched).toBe(false);
  });

  it("returns null when setup intent creation fails", async () => {
    apiClientMock.post.mockRejectedValueOnce(new Error("setup failed"));

    const paymentModule = await import("@/hooks/usePayment");
    const { result } = renderHook(() => paymentModule.useSetupIntent());

    let response: unknown;
    await act(async () => {
      response = await result.current.createSetupIntent();
    });

    expect(response).toBeNull();
    expect(result.current.error).toBe("setup failed");
  });

  it("treats missing subscription as null and supports lifecycle actions", async () => {
    apiClientMock.get.mockRejectedValueOnce({ response: { status: 404 } });
    apiClientMock.post.mockResolvedValueOnce({
      data: {
        id: "sub_1",
        plan: "pro",
        status: "active",
        cancel_at_period_end: false,
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
      },
    });
    apiClientMock.delete.mockResolvedValueOnce({ data: {} });
    apiClientMock.get.mockResolvedValueOnce({
      data: {
        id: "sub_1",
        plan: "pro",
        status: "active",
        cancel_at_period_end: true,
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
      },
    });
    apiClientMock.post.mockRejectedValueOnce(new Error("resume failed"));

    const paymentModule = await import("@/hooks/usePayment");
    const { result } = renderHook(() => paymentModule.useSubscription());

    await act(async () => {
      await result.current.fetchSubscription({ force: true });
    });

    expect(result.current.subscription).toBeNull();

    await act(async () => {
      await result.current.updateSubscription("pro", "pm_1");
    });

    expect(result.current.subscription?.plan).toBe("pro");
    expect(toastMock.success).toHaveBeenCalledWith("Plan updated", expect.any(Object));

    await act(async () => {
      await result.current.cancelSubscription(true);
    });

    expect(apiClientMock.delete).toHaveBeenCalledWith("/payment/subscription", {
      params: { cancel_immediately: true },
    });
    expect(toastMock.success).toHaveBeenCalledWith("Subscription cancelled", expect.any(Object));

    await act(async () => {
      await result.current.resumeSubscription();
    });

    expect(result.current.error).toBe("resume failed");
    expect(toastMock.error).toHaveBeenCalledWith("Failed to resume subscription", {
      description: "resume failed",
    });
  });

  it("surfaces plan loading failures", async () => {
    apiClientMock.get.mockRejectedValueOnce(new Error("plans unavailable"));

    const paymentModule = await import("@/hooks/usePayment");
    const { result } = renderHook(() => paymentModule.usePlans());

    await act(async () => {
      await result.current.fetchPlans();
    });

    expect(result.current.error).toBe("plans unavailable");
    expect(result.current.plans).toEqual([]);
  });
});
