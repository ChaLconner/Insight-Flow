import type { ReactNode } from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { afterAll, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import type { GoogleAuthButtonProps } from "@/components/auth/GoogleAuthButton";

const pathnameState = vi.hoisted(() => ({ value: "/" }));
const dynamicLoadPromises = vi.hoisted(() => [] as Promise<unknown>[]);

vi.mock("next/navigation", () => ({
  usePathname: () => pathnameState.value,
}));

vi.mock("@/components/providers/private-providers", () => ({
  PrivateProviders: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

vi.mock("@/components/auth/GoogleAuthButton", () => ({
  GoogleAuthButton: ({
    label,
    autoStart,
  }: {
    label: string;
    autoStart?: boolean;
  }) => (
    <div data-testid="loaded-google-auth" data-auto-start={String(autoStart)}>
      {label}
    </div>
  ),
}));

vi.mock("next/dynamic", () => ({
  default: (
    loader: () => Promise<unknown>,
    options?: { ssr?: boolean; loading?: () => unknown },
  ) => {
    dynamicLoadPromises.push(loader());
    options?.loading?.();

    if (options?.ssr === false) {
      return function MockGoogleAuthButton({
        label,
        autoStart,
      }: {
        label: string;
        autoStart?: boolean;
      }) {
        return (
          <div
            data-testid="loaded-google-auth"
            data-auto-start={String(autoStart)}
          >
            {label}
          </div>
        );
      };
    }

    return function MockPrivateProviders({ children }: { children: ReactNode }) {
      return <div data-testid="private-providers">{children}</div>;
    };
  },
}));

import { DeferredGoogleAuthButton } from "@/components/auth/DeferredGoogleAuthButton";
import { RouteProviders } from "@/components/providers/route-providers";

const initialGoogleClientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;

const googleButtonProps: GoogleAuthButtonProps = {
  label: "Continue with Google",
  title: "Sign in with Google",
  onError: vi.fn(),
  onNonOAuthError: vi.fn(),
  onSuccess: vi.fn(),
};

function renderDeferredGoogleButton(
  overrides: Partial<typeof googleButtonProps> = {},
) {
  return render(
    <DeferredGoogleAuthButton {...googleButtonProps} {...overrides} />,
  );
}

describe("route and deferred auth provider coverage", () => {
  beforeAll(async () => {
    await Promise.all(dynamicLoadPromises);
  });

  beforeEach(() => {
    pathnameState.value = "/";
    delete process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
  });

  afterAll(() => {
    if (initialGoogleClientId === undefined) {
      delete process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
    } else {
      process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID = initialGoogleClientId;
    }
  });

  it("renders landing content without private providers on public path", () => {
    pathnameState.value = "/";

    render(
      <RouteProviders>
        <span>Landing content</span>
      </RouteProviders>,
    );

    expect(screen.getByText("Landing content")).toBeInTheDocument();
    expect(screen.queryByTestId("private-providers")).not.toBeInTheDocument();
  });

  it("wraps private paths with private providers", () => {
    pathnameState.value = "/dashboard";

    render(
      <RouteProviders>
        <span>Dashboard content</span>
      </RouteProviders>,
    );

    expect(screen.getByTestId("private-providers")).toContainElement(
      screen.getByText("Dashboard content"),
    );
  });

  it("loads Google auth and starts immediately on click intent", () => {
    process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID = "test-client-id";
    renderDeferredGoogleButton();

    fireEvent.click(screen.getByRole("button", { name: googleButtonProps.label }));

    expect(screen.getByTestId("loaded-google-auth")).toHaveAttribute(
      "data-auto-start",
      "true",
    );
  });

  it("loads Google auth without auto-start on focus intent", () => {
    process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID = "test-client-id";
    renderDeferredGoogleButton();

    fireEvent.focus(screen.getByRole("button", { name: googleButtonProps.label }));

    expect(screen.getByTestId("loaded-google-auth")).toHaveAttribute(
      "data-auto-start",
      "false",
    );
  });

  it("loads Google auth on pointer-down intent", () => {
    process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID = "test-client-id";
    renderDeferredGoogleButton();

    fireEvent.pointerDown(
      screen.getByRole("button", { name: googleButtonProps.label }),
    );

    expect(screen.getByTestId("loaded-google-auth")).toBeInTheDocument();
  });

  it("loads Google auth on pointer-enter intent", () => {
    process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID = "test-client-id";
    renderDeferredGoogleButton();

    fireEvent.pointerEnter(
      screen.getByRole("button", { name: googleButtonProps.label }),
    );

    expect(screen.getByTestId("loaded-google-auth")).toBeInTheDocument();
  });

  it("does not load Google auth without a client ID", () => {
    renderDeferredGoogleButton();
    const button = screen.getByRole("button", { name: googleButtonProps.label });

    fireEvent.click(button);
    fireEvent.focus(button);
    fireEvent.pointerDown(button);
    fireEvent.pointerEnter(button);

    expect(screen.queryByTestId("loaded-google-auth")).not.toBeInTheDocument();
  });

  it("does not load Google auth when disabled", () => {
    process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID = "test-client-id";
    renderDeferredGoogleButton({ disabled: true });
    const button = screen.getByRole("button", { name: googleButtonProps.label });

    fireEvent.click(button);
    fireEvent.focus(button);
    fireEvent.pointerDown(button);
    fireEvent.pointerEnter(button);

    expect(button).toBeDisabled();
    expect(screen.queryByTestId("loaded-google-auth")).not.toBeInTheDocument();
  });
});
