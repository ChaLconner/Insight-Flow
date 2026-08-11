const LOCAL_APP_URL = "http://localhost:3000";

function normalizeBaseUrl(value: string): string {
  const trimmed = value.trim();
  if (trimmed.length === 0) {
    return "";
  }

  const withProtocol =
    trimmed.startsWith("http://") || trimmed.startsWith("https://")
      ? trimmed
      : `https://${trimmed}`;

  let normalized = withProtocol;
  while (normalized.endsWith("/")) {
    normalized = normalized.slice(0, -1);
  }
  return normalized;
}

export function resolveAppUrl(options?: {
  browserOrigin?: string;
  requestOrigin?: string;
}): string {
  const candidates = [
    process.env.NEXT_PUBLIC_APP_URL,
    process.env.VERCEL_PROJECT_PRODUCTION_URL,
    process.env.VERCEL_URL,
    options?.requestOrigin,
    options?.browserOrigin,
  ];

  for (const candidate of candidates) {
    if (!candidate) {
      continue;
    }

    const normalized = normalizeBaseUrl(candidate);
    if (normalized.length > 0) {
      return normalized;
    }
  }

  return LOCAL_APP_URL;
}
