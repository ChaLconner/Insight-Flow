import { act, render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AnimatedBackground } from "@/components/ui/animated-background";

const canvasContext = {
  arc: vi.fn(),
  beginPath: vi.fn(),
  clearRect: vi.fn(),
  fill: vi.fn(),
  getImageData: vi.fn(() => ({ data: new Uint8ClampedArray([0, 0, 0, 255]) })),
  lineTo: vi.fn(),
  moveTo: vi.fn(),
  restore: vi.fn(),
  save: vi.fn(),
  stroke: vi.fn(),
  set fillStyle(_value: string) {},
  set globalAlpha(_value: number) {},
  set lineWidth(_value: number) {},
  set shadowBlur(_value: number) {},
  set shadowColor(_value: string) {},
  set strokeStyle(_value: string) {},
};

describe("AnimatedBackground", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(
      canvasContext as unknown as CanvasRenderingContext2D,
    );
    vi.stubGlobal("requestAnimationFrame", vi.fn(() => 1));
    vi.stubGlobal("cancelAnimationFrame", vi.fn());
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("keeps canvas animation scheduled when leaving for bfcache", () => {
    render(<AnimatedBackground />);

    expect(HTMLCanvasElement.prototype.getContext).toHaveBeenCalledWith("2d");
    expect(window.requestAnimationFrame).toHaveBeenCalledTimes(1);

    act(() => {
      window.dispatchEvent(new Event("pagehide"));
    });

    expect(window.cancelAnimationFrame).not.toHaveBeenCalled();

    act(() => {
      window.dispatchEvent(new Event("pageshow"));
    });

    expect(window.cancelAnimationFrame).toHaveBeenCalledWith(1);
    expect(window.requestAnimationFrame).toHaveBeenCalledTimes(2);
  });

  it("recovers the canvas animation when the restored window receives focus", () => {
    render(<AnimatedBackground />);

    act(() => {
      window.dispatchEvent(new Event("focus"));
    });

    expect(window.cancelAnimationFrame).toHaveBeenCalledWith(1);
    expect(window.requestAnimationFrame).toHaveBeenCalledTimes(2);
  });

  it("does not rebuild a healthy animation from a blank pixel sample", () => {
    render(<AnimatedBackground />);

    expect(window.requestAnimationFrame).toHaveBeenCalledTimes(1);

    act(() => {
      vi.advanceTimersByTime(750);
    });

    expect(canvasContext.getImageData).not.toHaveBeenCalled();
    expect(window.cancelAnimationFrame).not.toHaveBeenCalled();
    expect(window.requestAnimationFrame).toHaveBeenCalledTimes(1);
  });

  it("renders a static frame without scheduling animation for reduced motion", () => {
    canvasContext.clearRect.mockClear();
    vi.spyOn(window, "matchMedia").mockImplementation((query) => ({
      matches: query.includes("prefers-reduced-motion"),
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));

    render(<AnimatedBackground />);

    expect(canvasContext.clearRect).toHaveBeenCalled();
    expect(window.requestAnimationFrame).not.toHaveBeenCalled();
  });
});
