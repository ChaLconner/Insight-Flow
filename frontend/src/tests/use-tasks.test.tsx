/**
 * Unit tests for useTasks hook.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { useTasks } from '@/hooks/use-tasks';

// Mock the auth store
vi.mock('@/stores/auth-store', () => ({
    useAuthStore: vi.fn(() => ({
        isAuthenticated: true,
    })),
}));

// Mock the tasksApi
vi.mock('@/lib/api-endpoints', () => ({
    tasksApi: {
        getProjectTasks: vi.fn(),
        getMyTasks: vi.fn(),
        updateTask: vi.fn(),
        updateProjectTask: vi.fn(),
        deleteTask: vi.fn(),
        deleteProjectTask: vi.fn(),
    },
}));

// Mock sonner toast
vi.mock('sonner', () => ({
    toast: {
        success: vi.fn(),
        error: vi.fn(),
    },
}));

import { tasksApi } from '@/lib/api-endpoints';

describe('useTasks hook', () => {
    let queryClient: QueryClient;

    const createWrapper = () => {
        queryClient = new QueryClient({
            defaultOptions: {
                queries: {
                    retry: false,
                },
            },
        });
        return ({ children }: { children: React.ReactNode }) => (
            <QueryClientProvider client={queryClient}>
                {children}
            </QueryClientProvider>
        );
    };

    beforeEach(() => {
        vi.clearAllMocks();
    });

    afterEach(() => {
        queryClient?.clear();
    });

    describe('fetching tasks', () => {
        it('should fetch my tasks when no projectId is provided', async () => {
            const mockResponse = {
                items: [
                    { id: '1', title: 'Task 1', status: 'todo' },
                    { id: '2', title: 'Task 2', status: 'in_progress' },
                ],
                total: 2,
                page: 1,
                size: 10,
                hasMore: false,
            };

            (tasksApi.getMyTasks as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse);

            const { result } = renderHook(() => useTasks(), {
                wrapper: createWrapper(),
            });

            expect(result.current.isLoading).toBe(true);

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(tasksApi.getMyTasks).toHaveBeenCalledWith(0, 10, '', 'all');
            expect(result.current.tasks).toHaveLength(2);
            expect(result.current.total).toBe(2);
        });

        it('should fetch project tasks when projectId is provided', async () => {
            const mockResponse = {
                items: [
                    { id: '1', title: 'Project Task 1', status: 'todo', projectId: 'proj-1' },
                ],
                total: 1,
                page: 1,
                size: 10,
                hasMore: false,
            };

            (tasksApi.getProjectTasks as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse);

            const { result } = renderHook(
                () => useTasks({ projectId: 'proj-1' }),
                { wrapper: createWrapper() }
            );

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(tasksApi.getProjectTasks).toHaveBeenCalledWith(
                'proj-1',
                0,
                10,
                undefined,
                undefined,
                '',
                'all'
            );
            expect(result.current.tasks).toHaveLength(1);
        });

        it('should handle pagination correctly', async () => {
            const mockResponse = {
                items: [{ id: '3', title: 'Task 3' }],
                total: 25,
                page: 2,
                size: 10,
                hasMore: true,
            };

            (tasksApi.getMyTasks as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse);

            const { result } = renderHook(
                () => useTasks({ page: 2, pageSize: 10 }),
                { wrapper: createWrapper() }
            );

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            // Skip should be (page - 1) * pageSize = (2 - 1) * 10 = 10
            expect(tasksApi.getMyTasks).toHaveBeenCalledWith(10, 10, '', 'all');
        });

        it('should handle search and filter', async () => {
            const mockResponse = {
                items: [],
                total: 0,
                page: 1,
                size: 10,
                hasMore: false,
            };

            (tasksApi.getMyTasks as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse);

            renderHook(
                () => useTasks({ searchQuery: 'test', statusFilter: 'done' }),
                { wrapper: createWrapper() }
            );

            await waitFor(() => {
                expect(tasksApi.getMyTasks).toHaveBeenCalledWith(0, 10, 'test', 'done');
            });
        });

        it('should not fetch when disabled', async () => {
            renderHook(
                () => useTasks({ enabled: false }),
                { wrapper: createWrapper() }
            );

            // Wait a bit to ensure no API call is made
            await new Promise((r) => setTimeout(r, 100));

            expect(tasksApi.getMyTasks).not.toHaveBeenCalled();
            expect(tasksApi.getProjectTasks).not.toHaveBeenCalled();
        });
    });

    describe('initial state', () => {
        it('should return correct initial state', () => {
            (tasksApi.getMyTasks as ReturnType<typeof vi.fn>).mockResolvedValue({
                items: [],
                total: 0,
                page: 1,
                size: 10,
                hasMore: false,
            });

            const { result } = renderHook(() => useTasks(), {
                wrapper: createWrapper(),
            });

            expect(result.current.tasks).toEqual([]);
            expect(result.current.total).toBe(0);
            expect(result.current.hasMore).toBe(false);
            expect(result.current.isDeleting).toBe(false);
            expect(result.current.isUpdating).toBe(false);
        });
    });

    describe('legacy response handling', () => {
        it('should handle array response format', async () => {
            const legacyResponse = [
                { id: '1', title: 'Legacy Task 1' },
                { id: '2', title: 'Legacy Task 2' },
            ];

            (tasksApi.getMyTasks as ReturnType<typeof vi.fn>).mockResolvedValue(legacyResponse);

            const { result } = renderHook(() => useTasks(), {
                wrapper: createWrapper(),
            });

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(result.current.tasks).toHaveLength(2);
            expect(result.current.total).toBe(2);
        });

        it('should handle { data: [...] } response format', async () => {
            const wrappedResponse = {
                data: [
                    { id: '1', title: 'Wrapped Task 1' },
                ],
            };

            (tasksApi.getMyTasks as ReturnType<typeof vi.fn>).mockResolvedValue(wrappedResponse);

            const { result } = renderHook(() => useTasks(), {
                wrapper: createWrapper(),
            });

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(result.current.tasks).toHaveLength(1);
        });
    });
});


describe('useTasks mutations', () => {
    let queryClient: QueryClient;

    const createWrapper = () => {
        queryClient = new QueryClient({
            defaultOptions: {
                queries: { retry: false },
                mutations: { retry: false },
            },
        });
        return ({ children }: { children: React.ReactNode }) => (
            <QueryClientProvider client={queryClient}>
                {children}
            </QueryClientProvider>
        );
    };

    beforeEach(() => {
        vi.clearAllMocks();
        // Setup default mock response
        (tasksApi.getMyTasks as ReturnType<typeof vi.fn>).mockResolvedValue({
            items: [{ id: '1', title: 'Test Task', projectId: null }],
            total: 1,
            page: 1,
            size: 10,
            hasMore: false,
        });
    });

    it('should provide updateTask mutation', async () => {
        const { result } = renderHook(() => useTasks(), {
            wrapper: createWrapper(),
        });

        await waitFor(() => {
            expect(result.current.isLoading).toBe(false);
        });

        expect(typeof result.current.updateTask).toBe('function');
    });

    it('should provide deleteTask mutation', async () => {
        const { result } = renderHook(() => useTasks(), {
            wrapper: createWrapper(),
        });

        await waitFor(() => {
            expect(result.current.isLoading).toBe(false);
        });

        expect(typeof result.current.deleteTask).toBe('function');
    });
});
