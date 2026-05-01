import { afterEach, describe, expect, it, vi } from "vitest";

describe("social-auth", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  it("builds the GitHub redirect URI from NEXT_PUBLIC_APP_URL", async () => {
    vi.stubEnv("NEXT_PUBLIC_APP_URL", "https://app.example.com/");
    const { getGitHubRedirectUri } = await import("@/lib/social-auth");

    expect(getGitHubRedirectUri()).toBe("https://app.example.com/auth/callback/github");
  });

  it("creates a cryptographically random OAuth state", async () => {
    const getRandomValues = vi.fn((bytes: Uint8Array) => {
      bytes.set(Array.from({ length: bytes.length }, (_, index) => index));
      return bytes;
    });
    vi.stubGlobal("crypto", { getRandomValues });
    const { createOAuthState } = await import("@/lib/social-auth");

    expect(createOAuthState()).toBe("000102030405060708090a0b0c0d0e0f");
    expect(getRandomValues).toHaveBeenCalledWith(expect.any(Uint8Array));
  });
});
