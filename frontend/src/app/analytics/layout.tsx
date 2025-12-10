import type { Metadata } from 'next';

export const metadata: Metadata = {
    title: 'Analytics | Insight Flow',
    description: 'View detailed analytics, team workload, and performance trends.',
};

export default function AnalyticsLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return <>{children}</>;
}
