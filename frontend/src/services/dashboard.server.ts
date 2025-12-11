import { cookies } from 'next/headers';

export async function getDashboardData() {
    const cookieStore = await cookies();
    const token = cookieStore.get('access_token')?.value;

    if (!token) {
        return null;
    }

    const apiUrl = process.env.API_URL ?? 'http://localhost:8000'; // Direct backend URL

    try {
        const res = await fetch(`${apiUrl}/dashboard/overview`, {
            headers: {
                Authorization: `Bearer ${token}`,
                'Content-Type': 'application/json',
            },
            next: { revalidate: 0 }, // Ensure fresh data on each request or use cache tags
        });

        if (!res.ok) {
            if (res.status === 401) { return null; }
            throw new Error('Failed to fetch dashboard data');
        }

        return res.json();
    } catch (error) {
        console.error('Error fetching dashboard data:', error);
        return null;
    }
}
