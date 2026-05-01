import { describe, expect, it } from "vitest";
import { getAuthRedirectUrl } from "@/lib/auth-redirect";

describe("auth-redirect", () => {
  it("uses safe relative callback redirects", () => {
    expect(getAuthRedirectUrl({ role: "admin", callbackUrl: "/settings" })).toBe(
      "/settings",
    );
  });

  it("falls back for external callback redirects", () => {
    expect(
      getAuthRedirectUrl({
        role: "member",
        callbackUrl: "https://evil.example/settings",
      }),
    ).toBe("/projects?tab=tasks");

    expect(
      getAuthRedirectUrl({
        role: "admin",
        callbackUrl: "//evil.example/settings",
      }),
    ).toBe("/dashboard");
  });
});
