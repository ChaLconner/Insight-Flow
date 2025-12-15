/**
 * Error Utils Tests
 * Tests for the error message extraction utility
 */
import { describe, it, expect } from "vitest";
import { getErrorMessage } from "@/lib/error-utils";
import { AxiosError, AxiosHeaders } from "axios";

describe("getErrorMessage", () => {
  it("extracts string detail from Axios error response", () => {
    const error = new AxiosError(
      "Request failed",
      "400",
      undefined,
      undefined,
      {
        data: { detail: "User not found" },
        status: 400,
        statusText: "Bad Request",
        headers: {},
        config: { headers: new AxiosHeaders() },
      },
    );

    expect(getErrorMessage(error)).toBe("User not found");
  });

  it("extracts message from Axios error response", () => {
    const error = new AxiosError(
      "Request failed",
      "400",
      undefined,
      undefined,
      {
        data: { message: "Invalid credentials" },
        status: 400,
        statusText: "Bad Request",
        headers: {},
        config: { headers: new AxiosHeaders() },
      },
    );

    expect(getErrorMessage(error)).toBe("Invalid credentials");
  });

  it("handles array of validation errors", () => {
    const error = new AxiosError(
      "Validation failed",
      "422",
      undefined,
      undefined,
      {
        data: {
          detail: [
            { msg: "Email is required" },
            { msg: "Password is too short" },
          ],
        },
        status: 422,
        statusText: "Unprocessable Entity",
        headers: {},
        config: { headers: new AxiosHeaders() },
      },
    );

    expect(getErrorMessage(error)).toBe(
      "Email is required, Password is too short",
    );
  });

  it("falls back to status text when no detail/message", () => {
    const error = new AxiosError(
      "Request failed",
      "500",
      undefined,
      undefined,
      {
        data: {},
        status: 500,
        statusText: "Internal Server Error",
        headers: {},
        config: { headers: new AxiosHeaders() },
      },
    );

    expect(getErrorMessage(error)).toBe(
      "Request failed: Internal Server Error",
    );
  });

  it("extracts message from standard Error", () => {
    const error = new Error("Something went wrong");
    expect(getErrorMessage(error)).toBe("Something went wrong");
  });

  it("returns string error as-is", () => {
    expect(getErrorMessage("Custom error message")).toBe(
      "Custom error message",
    );
  });

  it("returns default message for unknown error types", () => {
    expect(getErrorMessage({})).toBe(
      "An unexpected error occurred. Please try again.",
    );
    expect(getErrorMessage(null)).toBe(
      "An unexpected error occurred. Please try again.",
    );
    expect(getErrorMessage(undefined)).toBe(
      "An unexpected error occurred. Please try again.",
    );
    expect(getErrorMessage(123)).toBe(
      "An unexpected error occurred. Please try again.",
    );
  });

  it("handles validation errors with message field instead of msg", () => {
    const error = new AxiosError(
      "Validation failed",
      "422",
      undefined,
      undefined,
      {
        data: {
          detail: [{ message: "Field is invalid" }],
        },
        status: 422,
        statusText: "Unprocessable Entity",
        headers: {},
        config: { headers: new AxiosHeaders() },
      },
    );

    expect(getErrorMessage(error)).toBe("Field is invalid");
  });

  it("prioritizes detail over message", () => {
    const error = new AxiosError(
      "Request failed",
      "400",
      undefined,
      undefined,
      {
        data: {
          detail: "Specific error detail",
          message: "General message",
        },
        status: 400,
        statusText: "Bad Request",
        headers: {},
        config: { headers: new AxiosHeaders() },
      },
    );

    expect(getErrorMessage(error)).toBe("Specific error detail");
  });
});
