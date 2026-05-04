import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import LoginPage from "@/app/auth/login/page";

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
});
