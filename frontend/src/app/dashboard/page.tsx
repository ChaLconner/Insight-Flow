import { Metadata } from 'next';
import DashboardClient from './DashboardClient';
import { getDashboardData } from '@/services/dashboard.server';
import { QueryClient, HydrationBoundary, dehydrate } from '@tanstack/react-query';
import { dashboardKeys } from '@/hooks/use-dashboard';

export const metadata: Metadata = {
    title: 'Dashboard | Insight Flow',
    description: 'Overview of your projects, tasks, and team activity.',
};

export default async function DashboardPage() {
    const queryClient = new QueryClient();

    // Prefetch data on the server
    await queryClient.prefetchQuery({
        queryKey: dashboardKeys.overview(),
        queryFn: getDashboardData,
    });

    return (
        <HydrationBoundary state={dehydrate(queryClient)}>
            <DashboardClient />
        </HydrationBoundary>
    );
}
