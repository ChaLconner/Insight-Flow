import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ScrollReveal } from "@/components/landing/scroll-reveal";

describe("ScrollReveal", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "IntersectionObserver",
      class {
        private readonly observedTargets = new Set<Element>();

        constructor(private readonly callback: IntersectionObserverCallback) {}

        observe(target: Element) {
          this.observedTargets.add(target);
          this.callback(
            [{ isIntersecting: true, target } as IntersectionObserverEntry],
            this as unknown as IntersectionObserver,
          );
        }

        unobserve(target: Element) {
          this.observedTargets.delete(target);
        }
      },
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders its server-provided content without hiding it in the test environment", () => {
    render(
      <ScrollReveal className="content-boundary">
        <h2>Feature content</h2>
      </ScrollReveal>,
    );

    expect(screen.getByRole("heading", { name: "Feature content" })).toBeVisible();
    expect(screen.getByText("Feature content").parentElement).toHaveClass(
      "content-boundary",
    );
  });
});
