import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import AuthLayout from "@/app/auth/layout";

vi.mock("@/providers/google-auth-provider", () => ({
  GoogleAuthProvider: ({ children }: { children: React.ReactNode }) => (
    <>{children}</>
  ),
}));

vi.mock("next/script", () => ({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  default: ({ dangerouslySetInnerHTML, ...props }: any) => {
    return <script dangerouslySetInnerHTML={dangerouslySetInnerHTML} {...props} />;
  },
}));

vi.mock("@/components/ui/animated-background", () => ({
  AnimatedBackground: () => <div data-testid="animated-background" />,
  FloatingShapes: () => <div data-testid="floating-shapes" />,
}));

describe("AuthLayout theme isolation", () => {
  it("restores the previous root theme state when leaving auth routes", () => {
    const root = document.documentElement;
    root.className = "light custom-root";
    root.style.colorScheme = "light";
    root.setAttribute("data-theme", "light");
    root.setAttribute("data-color-scheme", "light");

    const { unmount } = render(
      <AuthLayout>
        <div>Auth page</div>
      </AuthLayout>,
    );

    expect(root).toHaveClass("dark");
    expect(root).not.toHaveClass("light");
    expect(root.style.colorScheme).toBe("dark");
    expect(root).toHaveAttribute("data-theme", "dark");
    expect(root).toHaveAttribute("data-color-scheme", "dark");

    unmount();

    expect(root.className).toBe("light custom-root");
    expect(root.style.colorScheme).toBe("light");
    expect(root).toHaveAttribute("data-theme", "light");
    expect(root).toHaveAttribute("data-color-scheme", "light");
  });

  it("removes auth-only theme attributes if the previous route did not have them", () => {
    const root = document.documentElement;
    root.className = "dark";
    root.style.colorScheme = "dark";
    root.removeAttribute("data-theme");
    root.removeAttribute("data-color-scheme");

    const { unmount } = render(
      <AuthLayout>
        <div>Auth page</div>
      </AuthLayout>,
    );

    unmount();

    expect(root.className).toBe("dark");
    expect(root.style.colorScheme).toBe("dark");
    expect(root).not.toHaveAttribute("data-theme");
    expect(root).not.toHaveAttribute("data-color-scheme");
  });

  it("forces a full page reload on bfcache restore (pageshow persisted=true)", () => {
    vi.useFakeTimers();

    const reloadSpy = vi.fn();
    Object.defineProperty(window, "location", {
      value: { ...window.location, reload: reloadSpy },
      writable: true,
    });

    const { unmount } = render(
      <AuthLayout>
        <div>Auth page</div>
      </AuthLayout>,
    );

    window.dispatchEvent(
      new PageTransitionEvent("pageshow", { persisted: true }),
    );

    // The reload is wrapped in setTimeout(fn, 0)
    vi.runAllTimers();
    expect(reloadSpy).toHaveBeenCalled();

    unmount();
    vi.useRealTimers();
  });

});
