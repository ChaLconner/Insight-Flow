import { useEffect } from "react";

export function isEditableEventTarget(target: EventTarget | null): target is HTMLElement {
  return (
    target instanceof HTMLElement &&
    (target.tagName === "INPUT" ||
      target.tagName === "TEXTAREA" ||
      target.isContentEditable)
  );
}

export function blurEditableTargetOnEscape(event: KeyboardEvent): boolean {
  const target = event.target;
  if (!isEditableEventTarget(target)) {
    return false;
  }

  if (event.key === "Escape") {
    target.blur();
  }

  return true;
}

export function useDocumentKeyDown(handler: (event: KeyboardEvent) => void) {
  useEffect(() => {
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [handler]);
}
