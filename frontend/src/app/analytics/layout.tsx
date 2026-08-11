import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Analytics",
  description:
    "View detailed analytics, team workload, and performance trends.",
};

export default function AnalyticsLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return <>{children}</>;
}
