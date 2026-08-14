import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { SkipLink } from "@/components/layout/SkipLink";

describe("SkipLink", () => {
  beforeEach(() => {
    window.history.replaceState(null, "", "/");
  });

  it("focuses the main content target when activated", () => {
    const scrollIntoView = vi.fn();
    render(
      <>
        <SkipLink />
        <main id="main-content" tabIndex={-1} ref={(node) => {
          if (node) {
            node.scrollIntoView = scrollIntoView;
          }
        }} />
      </>,
    );

    fireEvent.click(screen.getByRole("link", { name: "Skip to content" }));

    expect(document.activeElement).toHaveAttribute("id", "main-content");
    expect(scrollIntoView).toHaveBeenCalledWith({ block: "start" });
    expect(window.location.hash).toBe("#main-content");
  });
});
