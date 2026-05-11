import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import LoginPage from "@/app/auth/login/page";
import { apiClient } from "@/lib/api-client";
import { authActions } from "@/stores/auth-actions";

const replace = vi.fn();
let currentSearchParams = new URLSearchParams();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
  useSearchParams: () => currentSearchParams,
}));

vi.mock("@react-oauth/google", () => ({
  useGoogleLogin: () => vi.fn(),
}));

vi.mock("@/components/ui/animated-background", () => ({
  AnimatedBackground: () => <div data-testid="animated-background" />,
  FloatingShapes: () => <div data-testid="floating-shapes" />,
}));

vi.mock("@/lib/api-client", () => ({
  apiClient: {
    post: vi.fn(),
  },
}));

vi.mock("@/stores/auth-actions", () => ({
  authActions: {
    loginWithResponse: vi.fn(),
  },
}));

describe("LoginPage query prefills", () => {
  beforeEach(() => {
    replace.mockClear();
    vi.mocked(apiClient.post).mockReset();
    vi.mocked(authActions.loginWithResponse).mockReset();
    currentSearchParams = new URLSearchParams();
    window.sessionStorage.clear();
    process.env.NEXT_PUBLIC_GITHUB_CLIENT_ID = "github-client-id";
  });

  it("prefills credentials from local login query params and removes password from the URL", () => {
    currentSearchParams = new URLSearchParams({
      email: "admin@example.com",
      password: "password123",
      callbackUrl: "/dashboard",
    });

    render(<LoginPage />);

    expect(screen.getByLabelText(/email/i)).toHaveValue("admin@example.com");
    expect(screen.getByPlaceholderText("Enter your password")).toHaveValue(
      "password123",
    );
    expect(replace).toHaveBeenCalledWith(
      "/auth/login?email=admin%40example.com&callbackUrl=%2Fdashboard",
    );
  });

  it("renders GitHub OAuth as a button and navigates on click", async () => {
    currentSearchParams = new URLSearchParams({
      callbackUrl: "/dashboard",
    });

    render(<LoginPage />);

    const githubButton = screen.getByRole("button", {
      name: /continue with github/i,
    });

    expect(githubButton).toBeInTheDocument();
    expect(githubButton).toBeEnabled();
  });

  it("submits through a POST form and becomes interactive after hydration", async () => {
    render(<LoginPage />);

    const submitButton = screen.getByRole("button", { name: /sign in/i });
    expect(submitButton.closest("form")).toHaveAttribute("method", "post");

    await waitFor(() => {
      expect(submitButton).toBeEnabled();
    });
  });

  it("renders a link back to the landing page", () => {
    render(<LoginPage />);

    const landingLink = screen.getByRole("link", {
      name: /back to landing page/i,
    });

    expect(landingLink).toHaveAttribute("href", "/");
  });

  it("sends remember_me when Remember me is checked", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      data: {
        user: {
          id: "user-1",
          email: "admin@example.com",
          role: "admin",
        },
      },
    });

    render(<LoginPage />);

    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: "admin@example.com" },
    });
    fireEvent.change(screen.getByPlaceholderText("Enter your password"), {
      target: { value: "password123" },
    });
    fireEvent.click(screen.getByLabelText(/remember me/i));
    const submitButton = screen.getByRole("button", { name: /sign in/i });
    await waitFor(() => {
      expect(submitButton).toBeEnabled();
    });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith("/auth/login", {
        email: "admin@example.com",
        password: "password123",
        remember_me: true,
      });
    });
    expect(authActions.loginWithResponse).toHaveBeenCalledWith(
      expect.any(Object),
      { rememberMe: true },
    );
  });
});
