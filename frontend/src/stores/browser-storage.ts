import { createJSONStorage, type StateStorage } from "zustand/middleware";

const noopStorage: StateStorage = {
  getItem: () => null,
  setItem: () => undefined,
  removeItem: () => undefined,
};

export const browserJsonStorage = createJSONStorage(() =>
  typeof window === "undefined" ? noopStorage : window.localStorage,
);

const authPersistenceStorage: StateStorage = {
  getItem: (name) => {
    if (typeof window === "undefined") {
      return null;
    }

    return window.localStorage.getItem(name) ?? window.sessionStorage.getItem(name);
  },
  setItem: (name, value) => {
    if (typeof window === "undefined") {
      return;
    }

    let rememberMe = false;
    try {
      const parsed = JSON.parse(value) as { state?: { rememberMe?: unknown } };
      rememberMe = parsed.state?.rememberMe === true;
    } catch {
      rememberMe = false;
    }

    const primaryStorage = rememberMe ? window.localStorage : window.sessionStorage;
    const secondaryStorage = rememberMe ? window.sessionStorage : window.localStorage;

    primaryStorage.setItem(name, value);
    secondaryStorage.removeItem(name);
  },
  removeItem: (name) => {
    if (typeof window === "undefined") {
      return;
    }

    window.localStorage.removeItem(name);
    window.sessionStorage.removeItem(name);
  },
};

export const authJsonStorage = createJSONStorage(() =>
  typeof window === "undefined" ? noopStorage : authPersistenceStorage,
);
