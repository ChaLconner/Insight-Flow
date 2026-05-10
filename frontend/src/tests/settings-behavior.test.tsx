import React from "react";
import { act, fireEvent, render, renderHook, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { SubscriptionPlan, type PlanInfo } from "@/types";

const apiClientMock = {
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  delete: vi.fn(),
  patch: vi.fn(),
};

const usersApiMock = {
  getSettings: vi.fn(),
  updateSettings: vi.fn(),
  uploadAvatar: vi.fn(),
};

const updateUserProfileMock = vi.fn();
const updateUserAvatarMock = vi.fn();
const setThemeMock = vi.fn();

vi.mock("@/lib/api-client", () => ({
  apiClient: apiClientMock,
}));

vi.mock("@/lib/api-endpoints", () => ({
  usersApi: usersApiMock,
}));

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    loading: vi.fn(),
  },
}));

vi.mock("@/stores/auth-store", () => ({
  useAuthStore: vi.fn((selector?: (state: unknown) => unknown) => {
    const state = {
      isAuthenticated: true,
      isInitialized: true,
      user: {
        id: "user-1",
        firstName: "Jane",
        lastName: "Doe",
        email: "jane@example.com",
        username: "janedoe",
        phone: "+1234567890",
        bio: "Hello",
        avatar: "",
        name: "Jane Doe",
      },
      updateUserProfile: updateUserProfileMock,
      updateUserAvatar: updateUserAvatarMock,
    };

    return typeof selector === "function" ? selector(state) : state;
  }),
}));

vi.mock("@/hooks/use-theme", () => ({
  useTheme: () => ({
    currentTheme: "dark",
    setTheme: setThemeMock,
  }),
}));

vi.mock("next/image", () => ({
  default: (props: React.ImgHTMLAttributes<HTMLImageElement>) => <img {...props} alt={props.alt ?? ""} />,
}));

describe("settings behavior", () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    apiClientMock.get.mockReset();
    apiClientMock.post.mockReset();
    apiClientMock.put.mockReset();
    apiClientMock.delete.mockReset();
    apiClientMock.patch.mockReset();
    usersApiMock.getSettings.mockReset();
    usersApiMock.updateSettings.mockReset();
    usersApiMock.uploadAvatar.mockReset();

    try {
      const paymentModule = await import("@/hooks/usePayment");
      paymentModule.__clearPaymentCachesForTests?.();
    } catch {
      // Cache helpers are added by production code in the green step.
    }

    try {
      const billingModule = await import("@/hooks/useBillingData");
      billingModule.__clearBillingDataCacheForTests?.();
    } catch {
      // Cache helpers are added by production code in the green step.
    }

    try {
      const paymentHistoryModule = await import("@/app/settings/components/payment-history-settings");
      paymentHistoryModule.__clearPaymentHistoryCacheForTests?.();
    } catch {
      // Cache helpers are added by production code in the green step.
    }
  });

  it("reuses fresh payment methods cache across remounts", async () => {
    apiClientMock.get.mockResolvedValue({
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

    const paymentModule = await import("@/hooks/usePayment");
    const { result, unmount } = renderHook(() => paymentModule.usePaymentMethods());

    await act(async () => {
      await result.current.fetchMethods();
    });

    unmount();

    const secondMount = renderHook(() => paymentModule.usePaymentMethods());

    await act(async () => {
      await secondMount.result.current.fetchMethods();
    });

    expect(apiClientMock.get).toHaveBeenCalledTimes(1);
  });

  it("reuses fresh billing data cache across remounts", async () => {
    apiClientMock.get
      .mockResolvedValueOnce({
        data: {
          plans: [
            {
              plan: "free",
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
            },
          ],
        },
      })
      .mockResolvedValueOnce({
        data: {
          projects_used: 1,
          seats_used: 2,
        },
      });

    const billingModule = await import("@/hooks/useBillingData");
    const firstHook = renderHook(() => billingModule.useBillingData());

    await waitFor(() => expect(firstHook.result.current.isLoading).toBe(false));

    firstHook.unmount();

    const secondHook = renderHook(() => billingModule.useBillingData());

    await waitFor(() => expect(secondHook.result.current.isLoading).toBe(false));

    expect(apiClientMock.get).toHaveBeenCalledTimes(2);
  });

  it("reuses fresh payment history cache across remounts", async () => {
    apiClientMock.get
      .mockResolvedValueOnce({
        data: {
          total_spent: 120,
          total_payments: 2,
          successful_payments: 2,
          failed_payments: 0,
          pending_payments: 0,
          refunded_payments: 0,
          currency: "usd",
        },
      })
      .mockResolvedValueOnce({
        data: {
          payments: [],
          total: 0,
        },
      });

    const { PaymentHistorySettings } = await import("@/app/settings/components/payment-history-settings");
    const firstRender = render(<PaymentHistorySettings />);

    await waitFor(() => expect(apiClientMock.get).toHaveBeenCalledTimes(2));

    firstRender.unmount();
    render(<PaymentHistorySettings />);

    await waitFor(() => expect(screen.getByText("No payment history")).toBeInTheDocument());

    expect(apiClientMock.get).toHaveBeenCalledTimes(2);
  });

  it("persists appearance theme changes to user settings", async () => {
    usersApiMock.getSettings.mockResolvedValue({ theme: "dark" });
    usersApiMock.updateSettings.mockResolvedValue({ theme: "light" });

    const { AppearanceSettings } = await import("@/app/settings/components/appearance-settings");

    render(<AppearanceSettings />);

    fireEvent.click(screen.getByRole("button", { name: /light/i }));

    await waitFor(() =>
      expect(usersApiMock.updateSettings).toHaveBeenCalledWith({ theme: "light" }),
    );
  });

  it("reuses fresh downgrade eligibility checks", async () => {
    apiClientMock.get.mockResolvedValue({
      data: {
        can_downgrade: true,
        warnings: [],
      },
    });

    const { ChangePlanDialog, __clearDowngradeEligibilityCacheForTests } = await import(
      "@/app/settings/components/billing/ChangePlanDialog"
    );
    __clearDowngradeEligibilityCacheForTests?.();

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

    render(
      <ChangePlanDialog
        open
        onOpenChange={vi.fn()}
        currentPlan="pro"
        planConfig={proPlan}
        plans={{ free: freePlan, pro: proPlan }}
        plansLoading={false}
        methods={[]}
        selectedPaymentMethodId={null}
        onPaymentMethodChange={vi.fn()}
        onAddCard={vi.fn()}
        onConfirm={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Downgrade" }));

    await waitFor(() => expect(apiClientMock.get).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByRole("button", { name: "Back" }));
    fireEvent.click(screen.getByRole("button", { name: "Downgrade" }));

    await waitFor(() => expect(screen.getByRole("button", { name: "Back" })).toBeInTheDocument());
    expect(apiClientMock.get).toHaveBeenCalledTimes(1);
  });

  it("blocks profile save when phone number is invalid", async () => {
    const profileUtils = await import("@/app/settings/components/profile-settings.utils");

    expect(
      profileUtils.canSubmitProfileForm({
        hasUser: true,
        isSaving: false,
        isFormDirty: true,
        isEmailValid: true,
        isPhoneValid: false,
        isBioOverLimit: false,
      }),
    ).toBe(false);
  });
});
