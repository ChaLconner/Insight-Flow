type UserRole = string | null | undefined;

export function getPostLoginRedirect(role: UserRole, fallback = "/dashboard") {
  switch (role) {
    case "manager":
    case "viewer":
      return "/projects";
    case "member":
    case "user":
      return "/projects?tab=tasks";
    case "admin":
    default:
      return fallback;
  }
}

export function getAuthRedirectUrl({
  role,
  callbackUrl,
  fallback = "/dashboard",
}: {
  role: UserRole;
  callbackUrl?: string | null;
  fallback?: string;
}) {
  return callbackUrl ?? getPostLoginRedirect(role, fallback);
}

export function getSocialSignupRedirect(role: UserRole, isPaidPlan: boolean) {
  if (isPaidPlan) {
    return "/settings?tab=billing";
  }

  return getPostLoginRedirect(role);
}
