import { isAxiosError } from "axios";

/**
 * Extracts a user-friendly error message from various error objects.
 * Prioritizes backend structured error responses.
 */
export const getErrorMessage = (error: unknown): string => {
  if (isAxiosError(error)) {
    // Check for "detail" field (FastAPI default)
    if (error.response?.data?.detail) {
      if (typeof error.response.data.detail === "string") {
        return error.response.data.detail;
      }
      // Handle array of errors (e.g. validation errors)
      if (Array.isArray(error.response.data.detail)) {
        return error.response.data.detail
          .map(
            (err: { msg?: string; message?: string }) =>
              err.msg ?? err.message ?? JSON.stringify(err),
          )
          .join(", ");
      }
    }

    // Check for "message" field
    if (error.response?.data?.message) {
      return error.response.data.message;
    }

    // Fallback to status text
    if (error.response?.statusText) {
      return `Request failed: ${error.response.statusText}`;
    }
  }

  if (error instanceof Error) {
    return error.message;
  }

  if (typeof error === "string") {
    return error;
  }

  return "An unexpected error occurred. Please try again.";
};
