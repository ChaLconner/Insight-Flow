import { StateCreator } from "zustand";

export interface UserState {
  userPreferences: Record<string, unknown>;
  currentProjectId: string | null;
  setCurrentProjectId: (id: string | null) => void;
  updateUserPreferences: (preferences: Record<string, unknown>) => void;
  setUserPreferences: (preferences: Record<string, unknown>) => void;
}

export const createUserSlice: StateCreator<UserState> = (set) => ({
  userPreferences: {},
  currentProjectId: null,
  setCurrentProjectId: (id) => set({ currentProjectId: id }),
  updateUserPreferences: (preferences) =>
    set((state) => ({
      userPreferences: { ...state.userPreferences, ...preferences },
    })),
  setUserPreferences: (preferences) =>
    set((state) => ({
      userPreferences: { ...state.userPreferences, ...preferences },
    })),
});
