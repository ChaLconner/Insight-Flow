import { act, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { ReactNode } from "react";

const loadStripeMock = vi.hoisted(() => vi.fn());

vi.mock("@stripe/stripe-js/pure", () => ({
  loadStripe: loadStripeMock,
}));

vi.mock("@stripe/react-stripe-js", () => ({
  Elements: ({ children }: { children: ReactNode }) => (
    <div data-testid="stripe-elements">{children}</div>
  ),
}));

vi.mock("@/hooks/use-theme", () => ({
  useTheme: () => ({ isDarkMode: false }),
}));

vi.mock("@/components/billing/PaymentFormSkeleton", () => ({
  PaymentFormSkeleton: () => <div data-testid="stripe-skeleton" />,
}));

vi.mock("@/components/billing/StripeErrorBoundary", () => ({
  StripeErrorBoundary: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

describe("StripeProvider", () => {
  const originalKey = process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY;

  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
    process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY = "pk_test_example";
  });

  afterEach(() => {
    if (originalKey === undefined) {
      delete process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY;
    } else {
      process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY = originalKey;
    }
  });

  it("converts Stripe load rejection into retryable UI", async () => {
    let rejectStripe!: (reason?: unknown) => void;
    loadStripeMock.mockReturnValueOnce(new Promise<never>((_, reject) => {
      rejectStripe = reject;
    }));
    const { StripeProvider } = await import("@/components/providers/StripeProvider");

    render(
      <StripeProvider>
        <span>Payment content</span>
      </StripeProvider>,
    );

    await act(async () => {
      rejectStripe(new Error("Failed to load Stripe.js"));
    });

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/Stripe\.js could not be loaded/i);
    });
    expect(screen.queryByText("Payment content")).not.toBeInTheDocument();
  });

  it("does not render payment children until Stripe is ready", async () => {
    let resolveStripe!: (value: object) => void;
    loadStripeMock.mockReturnValueOnce(new Promise<object>((resolve) => {
      resolveStripe = resolve;
    }));
    const { StripeProvider } = await import("@/components/providers/StripeProvider");

    render(
      <StripeProvider>
        <span>Payment content</span>
      </StripeProvider>,
    );

    expect(screen.getByTestId("stripe-skeleton")).toBeInTheDocument();

    await act(async () => {
      resolveStripe({});
    });

    await waitFor(() => {
      expect(screen.getByTestId("stripe-elements")).toBeInTheDocument();
      expect(screen.getByText("Payment content")).toBeInTheDocument();
    });
  });
});
