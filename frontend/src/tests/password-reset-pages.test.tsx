import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ForgotPasswordPage from "@/app/auth/forgot-password/page";
import ResetPasswordPage from "@/app/auth/reset-password/page";
import { apiClient } from "@/lib/api-client";

let currentSearchParams = new URLSearchParams();

vi.mock("next/navigation", () => ({
  useSearchParams: () => currentSearchParams,
}));

vi.mock("@/lib/api-client", () => ({
  apiClient: {
    post: vi.fn(),
  },
}));

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

vi.mock("@/components/auth/AuthStatusIcon", () => ({
  AuthStatusIcon: ({ tone }: { tone: string }) => (
    <span data-testid={`auth-status-${tone}`} />
  ),
}));

describe("Password reset pages", () => {
  beforeEach(() => {
    vi.mocked(apiClient.post).mockReset();
    currentSearchParams = new URLSearchParams();
  });

  it("requests a password reset email with the entered address", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      data: { success: true },
    });

    render(<ForgotPasswordPage />);

    fireEvent.change(screen.getByLabelText(/email address/i), {
      target: { value: "member@example.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: /send reset link/i }));

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith("/auth/forgot-password", {
        email: "member@example.com",
      });
    });
    expect(await screen.findByText(/check your email/i)).toBeInTheDocument();
  });

  it("validates the reset token and submits the new password", async () => {
    currentSearchParams = new URLSearchParams("token=raw-reset-token");
    vi.mocked(apiClient.post).mockImplementation(async (url) => {
      if (url === "/auth/validate-reset-token") {
        return { data: { valid: true } };
      }
      return { data: { success: true } };
    });

    render(<ResetPasswordPage />);

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith(
        "/auth/validate-reset-token",
        { token: "raw-reset-token" },
      );
    });

    fireEvent.change(screen.getByLabelText(/^new password$/i), {
      target: { value: "NewPass123!" },
    });
    fireEvent.change(screen.getByLabelText(/confirm password/i), {
      target: { value: "NewPass123!" },
    });
    fireEvent.click(screen.getByRole("button", { name: /^reset password$/i }));

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith("/auth/reset-password", {
        token: "raw-reset-token",
        new_password: "NewPass123!",
      });
    });
    expect(
      await screen.findByText(/password reset successful/i),
    ).toBeInTheDocument();
  });
});
