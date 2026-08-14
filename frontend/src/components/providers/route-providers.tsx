"use client";

import dynamic from "next/dynamic";
import { usePathname } from "next/navigation";

const PrivateProviders = dynamic(
  () =>
    import("@/components/providers/private-providers").then(
      (module) => module.PrivateProviders,
    ),
  { loading: () => null },
);

export function isPublicLandingPath(pathname: string | null): boolean {
  return pathname === "/";
}

export function RouteProviders({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const pathname = usePathname();

  if (isPublicLandingPath(pathname)) {
    return children;
  }

  return <PrivateProviders>{children}</PrivateProviders>;
}
