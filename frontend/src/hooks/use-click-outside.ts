import { type RefObject, useEffect } from "react";

type DocumentPointerEvent = MouseEvent | TouchEvent;

function getElementFromEventTarget(target: EventTarget | null): Element | null {
  if (!(target instanceof Node)) {
    return null;
  }

  const node = target.nodeType === Node.TEXT_NODE ? target.parentNode : target;
  return node instanceof Element ? node : null;
}

export function useClickOutside<T extends HTMLElement>(
  ref: RefObject<T>,
  onClickOutside: () => void,
  enabled = true,
) {
  useEffect(() => {
    if (!enabled) {
      return;
    }

    const handlePointerDown = (event: DocumentPointerEvent) => {
      const target = event.target;
      if (ref.current && target instanceof Node && !ref.current.contains(target)) {
        onClickOutside();
      }
    };

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("touchstart", handlePointerDown);

    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("touchstart", handlePointerDown);
    };
  }, [enabled, onClickOutside, ref]);
}

export function useClickOutsideSelectors(
  selectors: string[],
  onClickOutside: () => void,
  enabled = true,
) {
  useEffect(() => {
    if (!enabled) {
      return;
    }

    const handlePointerDown = (event: DocumentPointerEvent) => {
      const element = getElementFromEventTarget(event.target);
      if (!element) {
        return;
      }

      if (!selectors.some((selector) => element.closest(selector))) {
        onClickOutside();
      }
    };

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("touchstart", handlePointerDown);

    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("touchstart", handlePointerDown);
    };
  }, [enabled, onClickOutside, selectors]);
}
