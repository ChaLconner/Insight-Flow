import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const cookieStore = vi.hoisted(() => ({
  getAll: vi.fn(),
}));
const incomingHeaders = vi.hoisted(() => new Headers());

vi.mock("next/headers", () => ({
  cookies: vi.fn(async () => cookieStore),
  headers: vi.fn(async () => incomingHeaders),
}));

import {
  buildServerRequestHeaders,
  resolveServerApiBaseUrl,
  serverApi,
} from "@/lib/api-server";
import { config, proxy, sanitizeForwardedHeaders } from "@/proxy";

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

function createToken(expiry = Math.floor(Date.now() / 1000) + 300) {
  const encode = (value: object) =>
    btoa(JSON.stringify(value))
      .replaceAll("+", "-")
      .replaceAll("/", "_")
      .replaceAll("=", "");

  return `${encode({ alg: "none", typ: "JWT" })}.${encode({ exp: expiry })}.signature`;
}

function requestFor(pathname: string, token?: string, search = "") {
  const request = new NextRequest(`http://localhost${pathname}${search}`);
  if (token) {
    request.cookies.set("access_token", token);
  }
  return request;
}

describe("route protection proxy", () => {
  it("skips API routes while preserving sanitized request headers", () => {
    const response = proxy(requestFor("/api/v1/health"));

    expect(response.status).toBe(200);
  });

  it("allows public routes without authentication", () => {
    for (const pathname of ["/auth/login", "/terms", "/privacy"]) {
      const response = proxy(requestFor(pathname));
      expect(response.status).toBe(200);
    }
  });

  it("redirects unauthenticated private routes to login with a return path", () => {
    const response = proxy(requestFor("/projects/123"));

    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toBe(
      "http://localhost/auth/login?redirect=%2Fprojects%2F123",
    );
  });

  it("does not add a dashboard redirect parameter for the dashboard route", () => {
    const response = proxy(requestFor("/dashboard"));

    expect(response.headers.get("location")).toBe("http://localhost/auth/login");
  });

  it("redirects authenticated auth pages to the dashboard", () => {
    const response = proxy(requestFor("/auth/register", createToken()));

    expect(response.headers.get("location")).toBe("http://localhost/dashboard");
  });

  it("clears tokens when an authenticated request explicitly logs out", () => {
    const response = proxy(
      requestFor("/auth/login", createToken(), "?logout=true"),
    );

    expect(response.status).toBe(200);
    expect(response.headers.get("set-cookie")).toContain("access_token");
    expect(response.headers.get("set-cookie")).toContain("refresh_token");
  });

  it("allows authenticated private routes", () => {
    const response = proxy(requestFor("/dashboard", createToken()));

    expect(response.status).toBe(200);
  });

  it("rejects malformed and expired access tokens", () => {
    expect(proxy(requestFor("/dashboard", "not-a-jwt")).status).toBe(307);
    expect(proxy(requestFor("/dashboard", createToken(Date.now() / 1000 - 1))).status).toBe(
      307,
    );
  });

  it("keeps the configured matcher as a raw string with literal backslashes", () => {
    expect(config.matcher[0]).toContain(String.raw`sw\.js`);
    expect(config.matcher[0]).toContain(String.raw`.*\.`);
  });
});

describe("server-side API adapter", () => {
  beforeEach(() => {
    cookieStore.getAll.mockReturnValue([
      { name: "access_token", value: "token" },
      { name: "refresh_token", value: "refresh" },
    ]);
    incomingHeaders.delete("x-forwarded-for");
    incomingHeaders.set("user-agent", "test-agent");
    vi.restoreAllMocks();
  });

  it("requires a non-loopback backend URL in production", () => {
    expect(() => resolveServerApiBaseUrl("", "production")).toThrow(
      "API_URL must be configured for production server-side API requests",
    );
    expect(() =>
      resolveServerApiBaseUrl("http://127.0.0.1:8000", "production"),
    ).toThrow("API_URL must not point to localhost");
  });

  it("normalizes backend API paths for server-side requests", () => {
    expect(
      resolveServerApiBaseUrl("https://api.example.test/api/v1", "production"),
    ).toBe("https://api.example.test/api/v1");
    expect(
      resolveServerApiBaseUrl("https://api.example.test/api", "production"),
    ).toBe("https://api.example.test/api/v1");
  });

  it("fetches and transforms projects while normalizing paths", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue({
        ok: true,
        json: async () => [{ id: "p1", name: "Project" }],
      } as Response);

    await expect(serverApi.getProjects()).resolves.toEqual([
      expect.objectContaining({ id: "p1", name: "Project" }),
    ]);
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/projects"),
      expect.objectContaining({ cache: "no-store" }),
    );
  });

  it("handles project and task adapter methods", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ id: "p1", name: "Project" }),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          items: [],
          total: 0,
          page: 1,
          size: 50,
          hasMore: false,
        }),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ id: "p1", name: "Project" }),
      } as Response);

    await expect(serverApi.getProject("p1")).resolves.toEqual(
      expect.objectContaining({ id: "p1", name: "Project" }),
    );
    await expect(serverApi.getProjectTasks("p1")).resolves.toEqual({
      items: [],
      total: 0,
      page: 1,
      size: 50,
      hasMore: false,
    });
    await expect(serverApi.getTask("t1")).resolves.toEqual({
      id: "p1",
      name: "Project",
    });
  });

  it.each([
    [404, "Not Found"],
    [401, "Unauthorized"],
    [500, "API Error: 500 Server Error"],
  ])("maps HTTP %s errors to stable exceptions", async (status, message) => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: false,
      status,
      statusText: status === 500 ? "Server Error" : "",
    } as Response);

    await expect(serverApi.getTask("t1")).rejects.toThrow(message);
  });

  it("returns an empty project list for a non-array response", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({ data: "not-an-array" }),
    } as Response);

    await expect(serverApi.getProjects()).resolves.toEqual([]);
  });
});
