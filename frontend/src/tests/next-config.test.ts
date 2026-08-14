import { afterEach, describe, expect, it, vi } from "vitest";

type Rewrite = {
  source: string;
  destination: string;
};

type NextConfig = {
  rewrites: () => Promise<Rewrite[]>;
};

const nextConfig = import("../../next.config.mjs").then(
  ({ default: config }) => config as NextConfig,
);

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("Next.js API proxy configuration", () => {
  it("keeps localhost fallback for development", async () => {
    vi.stubEnv("NODE_ENV", "development");
    vi.stubEnv("API_URL", "");
    vi.stubEnv("NEXT_PUBLIC_API_URL", "");

    const rewrites = await (await nextConfig).rewrites();

    expect(rewrites.at(-1)?.destination).toBe(
      "http://127.0.0.1:8000/api/v1/:path*",
    );
  });

  it("fails production builds when API origin is missing", async () => {
    vi.stubEnv("NODE_ENV", "production");
    vi.stubEnv("API_URL", "");
    vi.stubEnv("NEXT_PUBLIC_API_URL", "");

    await expect((await nextConfig).rewrites()).rejects.toThrow(
      "API_URL must be configured for production builds",
    );
  });

  it("does not treat the browser API base as the backend origin", async () => {
    vi.stubEnv("NODE_ENV", "production");
    vi.stubEnv("API_URL", "");
    vi.stubEnv("NEXT_PUBLIC_API_URL", "https://app.example.test/api");

    await expect((await nextConfig).rewrites()).rejects.toThrow(
      "API_URL must be configured for production builds",
    );
  });

  it("rejects loopback API origins in production", async () => {
    vi.stubEnv("NODE_ENV", "production");
    vi.stubEnv("API_URL", "http://127.0.0.1:8000");

    await expect((await nextConfig).rewrites()).rejects.toThrow(
      "API_URL must not point to localhost or another loopback host in production",
    );
  });

  it("normalizes an explicitly configured API path", async () => {
    vi.stubEnv("NODE_ENV", "production");
    vi.stubEnv("API_URL", "https://api.example.test/api/v1");

    const rewrites = await (await nextConfig).rewrites();

    expect(rewrites.at(-1)?.destination).toBe(
      "https://api.example.test/api/v1/:path*",
    );
  });
});
