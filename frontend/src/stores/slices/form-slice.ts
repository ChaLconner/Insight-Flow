import { StateCreator } from "zustand";

export interface FormData {
  [key: string]: unknown;
}

export interface FormState {
  activeForm: string | null;
  formData: Record<string, unknown>;
  formErrors: Record<string, string>;
  forms: Record<string, FormData>; // For backward compatibility
  
  setActiveForm: (formId: string | null) => void;
  updateFormData: (data: Record<string, unknown>) => void;
  setFormErrors: (errors: Record<string, string>) => void;
  clearFormData: (formId?: string) => void;
  updateForm: (formId: string, data: FormData) => void; // Alias
  clearForm: (formId: string) => void; // Alias
}

export const createFormSlice: StateCreator<FormState> = (set) => ({
  activeForm: null,
  formData: {},
  formErrors: {},
  forms: {},

  setActiveForm: (formId) => set({ activeForm: formId }),

  updateFormData: (data) =>
    set((state) => ({
      formData: { ...state.formData, ...data },
    })),

  setFormErrors: (errors) => set({ formErrors: errors }),

  clearFormData: (formId) =>
    set((state) => {
      if (formId && state.activeForm === formId) {
        return {
          activeForm: null,
          formData: {},
          formErrors: {},
        };
      }
      return state;
    }),

  updateForm: (formId, data) =>
    set((state) => ({
      forms: { ...state.forms, [formId]: data },
      formData: (data.data as Record<string, unknown>) || {},
      formErrors: (data.errors as Record<string, string>) || {},
    })),

  clearForm: (formId) =>
    set((state) => {
      const { [formId]: _removed, ...remainingForms } = state.forms;
      if (state.activeForm === formId) {
        return {
          activeForm: null,
          formData: {},
          formErrors: {},
          forms: remainingForms,
        };
      }
      return { forms: remainingForms };
    }),
});
