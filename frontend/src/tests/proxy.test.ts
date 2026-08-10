import { describe, expect, it } from "vitest";
import { buildServerRequestHeaders } from "@/lib/api-server";
import { sanitizeForwardedHeaders } from "@/proxy";

describe("proxy forwarded-header boundary", () => {
  it("removes client-controlled forwarding headers before upstream requests", () => {
    const sanitized = sanitizeForwardedHeaders(
      new Headers({
        forwarded: "for=203.0.113.10",
        "x-forwarded-for": "203.0.113.10",
        "x-real-ip": "203.0.113.10",
        "x-next-server-request": "1",
        "user-agent": "test-agent",
      }),
    );

    expect(sanitized.has("forwarded")).toBe(false);
    expect(sanitized.has("x-forwarded-for")).toBe(false);
    expect(sanitized.has("x-real-ip")).toBe(false);
    expect(sanitized.has("x-next-server-request")).toBe(false);
    expect(sanitized.get("user-agent")).toBe("test-agent");
  });

  it("forwards the Next.js-derived client IP for server-side backend calls", () => {
    const nextHeaders = new Headers({
      "user-agent": "test-agent",
      "x-forwarded-for": "203.0.113.10",
    });

    const outbound = buildServerRequestHeaders(nextHeaders, "access_token=token");

    expect(outbound.get("x-forwarded-for")).toBe("203.0.113.10");
    expect(outbound.get("cookie")).toBe("access_token=token");
    expect(outbound.get("x-next-server-request")).toBe("1");
  });

  it("does not forward a caller-supplied forwarding header when Next.js has none", () => {
    const outbound = buildServerRequestHeaders(
      new Headers({ "user-agent": "test-agent" }),
      "",
      { "x-forwarded-for": "198.51.100.20", "x-next-server-request": "spoofed" },
    );

    expect(outbound.has("x-forwarded-for")).toBe(false);
    expect(outbound.get("x-next-server-request")).toBe("1");
  });
});
