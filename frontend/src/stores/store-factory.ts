/**
 * Store Factory for Zustand - Staff/Principal Level State Management
 *
 * Provides:
 * - Consistent store creation with middleware composition
 * - DevTools integration
 * - Persist middleware with custom storage
 * - Immer for immutable updates
 * - Temporal (undo/redo) support
 * - Cross-tab synchronization
 */

import { create, StateCreator, StoreApi, UseBoundStore } from "zustand";
import { devtools, persist, PersistOptions } from "zustand/middleware";
import { immer } from "zustand/middleware/immer";
import { temporal } from "zundo";
import { browserJsonStorage } from "./browser-storage";

// =============================================================================
// Store Types
// =============================================================================

/**
 * Options for creating a store
 */
export interface StoreOptions<T> {
  /** Enable Redux DevTools integration */
  devtools?: boolean;

  /** Enable persistence to localStorage */
  persist?: boolean | PersistOptions<T, unknown>;

  /** Enable immer for immutable updates */
  immer?: boolean;

  /** Enable temporal (undo/redo) */
  temporal?: boolean;

  /** Enable cross-tab synchronization */
  syncTabs?: boolean;
}

/**
 * Store with temporal (undo/redo) capabilities
 */
export interface TemporalStore<T> {
  undo: () => void;
  redo: () => void;
  clear: () => void;
  futureStates: Partial<T>[];
  pastStates: Partial<T>[];
}

// =============================================================================
// Cross-Tab Synchronization
// =============================================================================

const tabSyncChannels = new Map<string, BroadcastChannel>();

/**
 * Create a BroadcastChannel for cross-tab sync
 */
function getTabSyncChannel(name: string): BroadcastChannel | null {
  if (typeof window === "undefined" || !("BroadcastChannel" in window)) {
    return null;
  }

  if (!tabSyncChannels.has(name)) {
    tabSyncChannels.set(name, new BroadcastChannel(`zustand-${name}`));
  }

  return tabSyncChannels.get(name) ?? null;
}

/**
 * Middleware for cross-tab synchronization
 */
const crossTabSync =
  <T extends object>(name: string) =>
  (config: StateCreator<T>): StateCreator<T> =>
  (set, get, api) => {
    const channel = getTabSyncChannel(name);

    if (channel) {
      // Listen for updates from other tabs
      channel.onmessage = (event) => {
        if (event.data.type === "state-update") {
          set(event.data.state, true);
        }
      };

      // Override set to broadcast to other tabs
      const originalSet = set;
      const syncedSet: typeof set = (partial, replace) => {
        originalSet(partial, replace);

        // Broadcast to other tabs
        try {
          const state = get();
          channel.postMessage({ type: "state-update", state });
        } catch {
          // Ignore serialization errors
        }
      };

      return config(syncedSet, get, api);
    }

    return config(set, get, api);
  };

// =============================================================================
// Store Factory
// =============================================================================

/**
 * Create a Zustand store with configurable middleware.
 *
 * @example
 * // Basic store
 * const useStore = createStore({
 *   name: 'counter',
 *   initializer: (set) => ({
 *     count: 0,
 *     increment: () => set((state) => ({ count: state.count + 1 })),
 *   }),
 * });
 *
 * // With all middleware
 * const useStore = createStore({
 *   name: 'todos',
 *   initializer: (set) => ({ ... }),
 *   options: {
 *     devtools: true,
 *     persist: true,
 *     immer: true,
 *     temporal: true,
 *     syncTabs: true,
 *   },
 * });
 */
export function createStore<T extends object>({
  name,
  initializer,
  options = {},
}: {
  name: string;
  initializer: StateCreator<T, [], []>;
  options?: StoreOptions<T>;
}): UseBoundStore<StoreApi<T>> {
  const {
    devtools: enableDevtools = process.env.NODE_ENV === "development",
    persist: enablePersist = false,
    immer: enableImmer = false,
    temporal: enableTemporal = false,
    syncTabs: enableSyncTabs = false,
  } = options;

  // Build middleware chain
   
  let storeCreator: any = initializer;

  // Apply immer first (innermost)
  if (enableImmer) {
    const prevCreator = storeCreator;
    storeCreator = immer(prevCreator);
  }

  // Apply temporal
  if (enableTemporal) {
    const prevCreator = storeCreator;
    storeCreator = temporal(prevCreator, { limit: 50 });
  }

  // Apply cross-tab sync
  if (enableSyncTabs) {
    const prevCreator = storeCreator;
    storeCreator = crossTabSync<T>(name)(prevCreator);
  }

  // Apply persist
  if (enablePersist) {
    const persistOptions: PersistOptions<T, unknown> =
      typeof enablePersist === "object"
        ? { storage: browserJsonStorage, ...enablePersist }
        : {
            name: `insight-flow-${name}`,
            version: 1,
            storage: browserJsonStorage,
          };

    const prevCreator = storeCreator;
    storeCreator = persist(prevCreator, persistOptions);
  }

  // Apply devtools (outermost)
  if (enableDevtools) {
    const prevCreator = storeCreator;
    storeCreator = devtools(prevCreator, { name, enabled: true });
  }

  return create(storeCreator);
}

// =============================================================================
// Slice Pattern Helper
// =============================================================================

/**
 * Helper type for creating store slices.
 *
 * @example
 * const createUserSlice: SliceCreator<UserSlice> = (set)=> ({
 *   user: null,
 *   setUser: (user) => set({ user }),
 * });
 */
export type SliceCreator<T, Middlewares extends any[] = []> = StateCreator<
  T,
  Middlewares,
  [],
  T
>;

/**
 * Combine multiple slices into a single store.
 *
 * @example
 * const useStore = createCombinedStore({
 *   name: 'app',
 *   slices: {
 *     user: createUserSlice,
 *     settings: createSettingsSlice,
 *   },
 * });
 */
export function createCombinedStore<T extends object>({
  name,
  slices,
  options = {},
}: {
  name: string;
  slices: Record<string, StateCreator<Partial<T>, [], [], Partial<T>>>;
  options?: StoreOptions<T>;
}): UseBoundStore<StoreApi<T>> {
  const combinedInitializer: StateCreator<T, [], []> = (set, get, api) => {
    const result: Partial<T> = {};

    for (const [, createSlice] of Object.entries(slices)) {
      Object.assign(
        result,
        createSlice(set as never, get as never, api as never)
      );
    }

    return result as T;
  };

  return createStore({
    name,
    initializer: combinedInitializer,
    options,
  });
}

// =============================================================================
// Selector Helpers
// =============================================================================

/**
 * Create a memoized selector.
 *
 * @example
 * const selectUserName = createSelector(
 *   (state: AppState) => state.user,
 *   (user) => user?.name ?? 'Guest'
 * );
 */
export function createSelector<T, R>(
  selector: (state: T) => R
): (state: T) => R {
  let lastState: T | undefined;
  let lastResult: R | undefined;

  return (state: T): R => {
    if (state === lastState) {
      return lastResult!;
    }

    lastState = state;
    lastResult = selector(state);
    return lastResult;
  };
}

/**
 * Create a shallow equality selector for objects.
 */
export function createShallowSelector<T, R extends object>(
  selector: (state: T) => R
): (state: T) => R {
  let lastResult: R | undefined;

  return (state: T): R => {
    const newResult = selector(state);

    if (lastResult && shallowEqual(lastResult, newResult)) {
      return lastResult;
    }

    lastResult = newResult;
    return newResult;
  };
}

/**
 * Shallow equality check for objects
 */
function shallowEqual<T extends object>(a: T, b: T): boolean {
  if (a === b) {
    return true;
  }

  const keysA = Object.keys(a);
  const keysB = Object.keys(b);

  if (keysA.length !== keysB.length) {
    return false;
  }

  for (const key of keysA) {
    if ((a as Record<string, unknown>)[key] !== (b as Record<string, unknown>)[key]) {
      return false;
    }
  }

  return true;
}

// =============================================================================
// Testing Utilities
// =============================================================================

/**
 * Create a test wrapper for a store.
 *
 * @example
 * const { store, reset } = createTestStore(useAuthStore);
 * afterEach(() => reset());
 */
export function createTestStore<T>(
  useStore: UseBoundStore<StoreApi<T>>
): {
  store: UseBoundStore<StoreApi<T>>;
  reset: () => void;
  setState: (partial: Partial<T>) => void;
  getState: () => T;
} {
  const initialState = useStore.getState();

  return {
    store: useStore,
    reset: () => useStore.setState(initialState, true),
    setState: (partial) => useStore.setState(partial),
    getState: () => useStore.getState(),
  };
}

// =============================================================================
// Type Exports
// =============================================================================

export type {
  StateCreator,
  StoreApi,
  UseBoundStore,
  PersistOptions,
};
