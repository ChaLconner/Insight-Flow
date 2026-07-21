/**
 * Comprehensive tests for API Client (Native Fetch Implementation)
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  apiClient,
  createFormData,
  createDeduplicatedRequest,
  createCustomApiClient,
  checkBackendHealth,
  isAxiosError,
  ApiError,
} from '@/lib/api-client';

describe('API Client Configuration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should be defined', () => {
    expect(apiClient).toBeDefined();
  });

  it('should handle successful GET responses via fetch', async () => {
    const mockData = { success: true, id: 123 };
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify(mockData), {
        status: 200,
        statusText: 'OK',
        headers: { 'Content-Type': 'application/json' },
      })
    );

    const res = await apiClient.get('/test');
    expect(res.status).toBe(200);
    expect(res.data).toEqual(mockData);
  });

  it('should handle error responses and throw ApiError', async () => {
    const errorBody = { detail: 'Unauthorized access' };
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify(errorBody), {
        status: 401,
        statusText: 'Unauthorized',
        headers: { 'Content-Type': 'application/json' },
      })
    );

    await expect(apiClient.get('/auth/login')).rejects.toThrow();
  });

  it('should identify ApiError with isAxiosError helper for backward compatibility', () => {
    const err = new ApiError('Test error', {
      data: {},
      status: 400,
      statusText: 'Bad Request',
      headers: {},
    });
    expect(isAxiosError(err)).toBe(true);
  });

  it('should create form data from mixed values', () => {
    const file = new File(['hello'], 'hello.txt', { type: 'text/plain' });
    const formData = createFormData({
      title: 'Report',
      count: 2,
      active: true,
      file,
      tags: ['alpha', 'beta'],
      meta: { owner: 'qa' },
      empty: null,
    });

    expect(formData.get('title')).toBe('Report');
    expect(formData.get('count')).toBe('2');
    expect(formData.get('active')).toBe('true');
    expect(formData.get('file')).toBe(file);
    expect(formData.get('tags[0]')).toBe('alpha');
    expect(formData.get('tags[1]')).toBe('beta');
    expect(formData.get('meta')).toBe(JSON.stringify({ owner: 'qa' }));
    expect(formData.has('empty')).toBe(false);
  });

  it('should deduplicate concurrent requests by cache key', async () => {
    const requestFn = vi.fn().mockResolvedValue('ok');

    const first = createDeduplicatedRequest(requestFn, 'projects');
    const second = createDeduplicatedRequest(requestFn, 'projects');

    await expect(first).resolves.toBe('ok');
    await expect(second).resolves.toBe('ok');
    expect(requestFn).toHaveBeenCalledTimes(1);
  });

  it('should remove failed deduplicated requests from cache', async () => {
    const requestFn = vi
      .fn()
      .mockRejectedValueOnce(new Error('fail'))
      .mockResolvedValueOnce('recovered');

    await expect(createDeduplicatedRequest(requestFn, 'retry-key')).rejects.toThrow('fail');
    await expect(createDeduplicatedRequest(requestFn, 'retry-key')).resolves.toBe('recovered');
    expect(requestFn).toHaveBeenCalledTimes(2);
  });

  it('should create custom API clients', () => {
    const client = createCustomApiClient('http://api.test', 2500);
    expect(client).toBeDefined();
    expect(typeof client.get).toBe('function');
    expect(typeof client.post).toBe('function');
  });

  it('should report backend health status', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify({ status: 'healthy' }), {
        status: 200,
        statusText: 'OK',
      })
    );

    const isHealthy = await checkBackendHealth();
    expect(isHealthy).toBe(true);
  });
});
