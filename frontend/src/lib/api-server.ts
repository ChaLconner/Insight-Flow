import { cookies, headers } from "next/headers";
import type { Task, TaskListResponse } from "@/types";
import { transformProjectData } from "@/lib/project-utils";

const LOCAL_API_BASE_URL = "http://127.0.0.1:8000/api/v1";

function isLoopbackHost(hostname: string): boolean {
  return ["localhost", "127.0.0.1", "::1"].includes(
    hostname.replace(/^\[|\]$/g, "").toLowerCase(),
  );
}

export function resolveServerApiBaseUrl(
  configuredApiUrl = process.env.API_URL,
  environment = process.env.NODE_ENV,
): string {
  const apiUrl = configuredApiUrl?.trim();
  if (!apiUrl) {
    if (environment === "production") {
      throw new Error(
        "API_URL must be configured for production server-side API requests.",
      );
    }
    return LOCAL_API_BASE_URL;
  }

  let parsedUrl: URL;
  try {
    parsedUrl = new URL(apiUrl);
  } catch {
    throw new Error("API_URL must be an absolute http(s) URL.");
  }

  if (!["http:", "https:"].includes(parsedUrl.protocol)) {
    throw new Error("API_URL must use the http or https protocol.");
  }
  if (parsedUrl.search || parsedUrl.hash) {
    throw new Error("API_URL must not include a query string or fragment.");
  }
  if (environment === "production" && isLoopbackHost(parsedUrl.hostname)) {
    throw new Error(
      "API_URL must not point to localhost or another loopback host in production.",
    );
  }

  const pathName = parsedUrl.pathname.replace(/\/+$/, "");
  if (pathName !== "" && pathName !== "/api" && pathName !== "/api/v1") {
    throw new Error("API_URL must point to the API origin, not an API route.");
  }
  parsedUrl.pathname = "/api/v1";
  return parsedUrl.toString().replace(/\/$/, "");
}

// Use backend directly for server-side fetching to avoid proxy loopback overhead.
const SERVER_BASE_URL = resolveServerApiBaseUrl();

export function buildServerRequestHeaders(
  incomingHeaders: Headers,
  cookieHeader: string,
  optionsHeaders?: HeadersInit,
): Headers {
  const outboundHeaders = new Headers(optionsHeaders);

  // Never trust forwarding headers supplied by a caller. The proxy removes
  // client-supplied values before Next.js renders the request; the value read
  // here is the trusted value populated by Next.js from its request socket or
  // configured upstream proxy.
  outboundHeaders.delete("Forwarded");
  outboundHeaders.delete("X-Forwarded-For");
  outboundHeaders.delete("X-Real-IP");

  const forwardedFor = incomingHeaders.get("x-forwarded-for");
  if (forwardedFor) {
    outboundHeaders.set("X-Forwarded-For", forwardedFor);
  }

  outboundHeaders.set("Content-Type", "application/json");
  outboundHeaders.set("Cookie", cookieHeader);
  outboundHeaders.set("User-Agent", incomingHeaders.get("user-agent") ?? "");
  // The browser's socket identity is lost when Next.js performs this server-
  // side hop. The backend accepts this marker only from a trusted proxy, and
  // proxy.ts removes client-supplied copies before rendering.
  outboundHeaders.set("X-Next-Server-Request", "1");
  return outboundHeaders;
}

async function fetchServer<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const cookieStore = await cookies();
  const headersStore = await headers();
  
  const allCookies = cookieStore
    .getAll()
    .map((c) => `${c.name}=${c.value}`)
    .join("; ");

  const outboundHeaders = buildServerRequestHeaders(headersStore, allCookies, options.headers);

  // Standardize path to ensure it starts with / but doesn't duplicate
  const cleanPath = path.startsWith("/") ? path : `/${path}`;

  /* console.log(`[fetchServer] Requesting: ${SERVER_BASE_URL}${cleanPath}`);
  console.log(`[fetchServer] Cookies present: ${cookieStore.getAll().map(c => c.name).join(', ')}`); */

  const res = await fetch(`${SERVER_BASE_URL}${cleanPath}`, {
    ...options,
    headers: outboundHeaders,
    cache: "no-store", // Default to dynamic for authenticated data
  });

  if (!res.ok) {
    // We can enhance this to throw specific errors or return null
    if (res.status === 404) {
      throw new Error("Not Found");
    }
    if (res.status === 401) {
      throw new Error("Unauthorized");
    }
    throw new Error(`API Error: ${res.status} ${res.statusText}`);
  }

  const data = await res.json();
  return data;
}

export const serverApi = {
  getProjects: async () => {
    const data = await fetchServer<unknown[]>("/projects");
    return Array.isArray(data)
      ? data.map((p, index) => transformProjectData(p, undefined, index))
      : [];
  },
  getProject: async (id: string) => {
    const data = await fetchServer(`/projects/${id}`);
    return transformProjectData(data);
  },
  getProjectTasks: (projectId: string) =>
    fetchServer<TaskListResponse>(`/projects/${projectId}/tasks?limit=50`),
  getTask: (id: string) => fetchServer<Task>(`/tasks/${id}`),
};
