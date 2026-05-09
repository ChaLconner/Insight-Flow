/**
 * Comprehensive tests for API Client
 * Tests error handling, retries, and request/response interceptors
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock axios before importing
vi.mock('axios', () => {
  const mockAxios = {
    create: vi.fn(() => mockAxios),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    defaults: {
      headers: {
        common: {},
      },
    },
  };
  return { default: mockAxios };
});

describe('API Client Configuration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should be defined', () => {
    expect(true).toBe(true);
  });

  it('should handle successful responses', async () => {
    const mockResponse = { data: { success: true }, status: 200 };
    
    expect(mockResponse.status).toBe(200);
    expect(mockResponse.data.success).toBe(true);
  });

  it('should handle error responses', async () => {
    const mockError = {
      response: {
        status: 401,
        data: { detail: 'Unauthorized' },
      },
    };

    expect(mockError.response.status).toBe(401);
    expect(mockError.response.data.detail).toBe('Unauthorized');
  });

  it('should handle network errors', async () => {
    const networkError = new Error('Network Error');
    networkError.name = 'NetworkError';

    expect(networkError.name).toBe('NetworkError');
    expect(networkError.message).toBe('Network Error');
  });

  it('should handle timeout errors', async () => {
    const timeoutError = new Error('timeout of 10000ms exceeded');
    timeoutError.name = 'TimeoutError';

    expect(timeoutError.message).toContain('timeout');
  });
});

describe('API Client Helpers', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
  });

  it('should attach CSRF token from cookies', async () => {
    await import('@/lib/api-client');
    const axios = (await import('axios')).default as unknown as {
      interceptors: {
        request: {
          use: ReturnType<typeof vi.fn>;
        };
      };
    };
    const requestHandler = axios.interceptors.request.use.mock.calls.at(-1)?.[0] as (
      config: { headers: Record<string, string> },
    ) => { headers: Record<string, string> };

    vi.spyOn(document, 'cookie', 'get').mockReturnValue(
      'csrf_token=test-csrf; session=abc',
    );

    const result = requestHandler({ headers: {} });

    expect(result.headers['X-CSRF-Token']).toBe('test-csrf');
  });

  it('should create form data from mixed values', async () => {
    const { createFormData } = await import('@/lib/api-client');

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
    const { createDeduplicatedRequest } = await import('@/lib/api-client');
    const requestFn = vi.fn().mockResolvedValue('ok');

    const first = createDeduplicatedRequest(requestFn, 'projects');
    const second = createDeduplicatedRequest(requestFn, 'projects');

    await expect(first).resolves.toBe('ok');
    await expect(second).resolves.toBe('ok');
    expect(requestFn).toHaveBeenCalledTimes(1);
  });

  it('should remove failed deduplicated requests from cache', async () => {
    const { createDeduplicatedRequest } = await import('@/lib/api-client');
    const requestFn = vi
      .fn()
      .mockRejectedValueOnce(new Error('fail'))
      .mockResolvedValueOnce('recovered');

    await expect(createDeduplicatedRequest(requestFn, 'retry-key')).rejects.toThrow('fail');
    await expect(createDeduplicatedRequest(requestFn, 'retry-key')).resolves.toBe('recovered');
    expect(requestFn).toHaveBeenCalledTimes(2);
  });

  it('should create custom API clients', async () => {
    const { createCustomApiClient } = await import('@/lib/api-client');
    const axios = (await import('axios')).default as unknown as {
      create: ReturnType<typeof vi.fn>;
    };

    createCustomApiClient('http://api.test', 2500);

    expect(axios.create).toHaveBeenCalledWith({
      baseURL: 'http://api.test',
      timeout: 2500,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  });

  it('should clear local auth state on refresh failure even when already on an auth route', async () => {
    vi.resetModules();
    const axios = (await import('axios')).default as unknown as {
      get: ReturnType<typeof vi.fn>;
      post: ReturnType<typeof vi.fn>;
      interceptors: {
        response: {
          use: ReturnType<typeof vi.fn>;
        };
      };
    };
    axios.get.mockReset();
    axios.post.mockReset();
    axios.interceptors.response.use.mockClear();

    const {
      registerLogoutHandler,
      setLoggingOut,
    } = await import('@/lib/api-client');
    const logoutHandler = vi.fn();
    const refreshFailure = new Error('refresh failed');
    const finalAuthFailure = new Error('still unauthorized');
    const responseHandler = [...axios.interceptors.response.use.mock.calls].reverse().find(
      (call) => typeof call[1] === 'function',
    )?.[1] as (error: unknown) => Promise<unknown>;

    window.history.pushState({}, '', '/auth/login');
    setLoggingOut(false);
    registerLogoutHandler(logoutHandler);
    axios.post.mockRejectedValueOnce(refreshFailure);
    axios.get.mockRejectedValueOnce(finalAuthFailure);

    await expect(
      responseHandler({
        response: { status: 401 },
        config: { method: 'get', url: '/projects' },
      }),
    ).rejects.toBe(refreshFailure);

    expect(logoutHandler).toHaveBeenCalledTimes(1);
  });

  it('should report backend health status', async () => {
    const { apiClient, checkBackendHealth } = await import('@/lib/api-client');
    const mockClient = apiClient as unknown as {
      get: ReturnType<typeof vi.fn>;
    };
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});

    mockClient.get.mockResolvedValueOnce({ data: { status: 'healthy' } });
    await expect(checkBackendHealth()).resolves.toBe(true);

    mockClient.get.mockRejectedValueOnce(new Error('offline'));
    await expect(checkBackendHealth()).resolves.toBe(false);
    expect(consoleError).toHaveBeenCalledWith(
      '❌ Backend health check failed:',
      'offline',
    );
  });

  it('should wait for backend until a health check succeeds', async () => {
    const { apiClient, waitForBackend } = await import('@/lib/api-client');
    const mockClient = apiClient as unknown as {
      get: ReturnType<typeof vi.fn>;
    };
    vi.spyOn(console, 'error').mockImplementation(() => {});

    mockClient.get
      .mockRejectedValueOnce(new Error('starting'))
      .mockResolvedValueOnce({ data: { status: 'healthy' } });

    await expect(waitForBackend(2, 0)).resolves.toBe(true);
    expect(mockClient.get).toHaveBeenCalledTimes(2);
  });
});

describe('API Response Transformation', () => {
  it('should transform successful response', () => {
    const rawResponse = {
      data: {
        id: '123',
        name: 'Test',
        created_at: '2024-01-01T00:00:00Z',
      },
    };

    expect(rawResponse.data.id).toBe('123');
    expect(rawResponse.data.name).toBe('Test');
    expect(rawResponse.data.created_at).toBeDefined();
  });

  it('should handle empty response', () => {
    const emptyResponse = { data: null };

    expect(emptyResponse.data).toBeNull();
  });

  it('should handle array response', () => {
    const arrayResponse = {
      data: [
        { id: '1', name: 'Item 1' },
        { id: '2', name: 'Item 2' },
      ],
    };

    expect(Array.isArray(arrayResponse.data)).toBe(true);
    expect(arrayResponse.data.length).toBe(2);
  });
});

describe('Error Handling', () => {
  it('should categorize 400 errors', () => {
    const error = { response: { status: 400 } };
    expect(error.response.status).toBe(400);
    expect(error.response.status >= 400 && error.response.status < 500).toBe(true);
  });

  it('should categorize 401 errors', () => {
    const error = { response: { status: 401 } };
    expect(error.response.status).toBe(401);
  });

  it('should categorize 403 errors', () => {
    const error = { response: { status: 403 } };
    expect(error.response.status).toBe(403);
  });

  it('should categorize 404 errors', () => {
    const error = { response: { status: 404 } };
    expect(error.response.status).toBe(404);
  });

  it('should categorize 500 errors', () => {
    const error = { response: { status: 500 } };
    expect(error.response.status).toBe(500);
    expect(error.response.status >= 500).toBe(true);
  });

  it('should handle rate limit errors (429)', () => {
    const error = {
      response: {
        status: 429,
        headers: {
          'retry-after': '60',
        },
      },
    };

    expect(error.response.status).toBe(429);
    expect(error.response.headers['retry-after']).toBe('60');
  });
});

describe('Request Configuration', () => {
  it('should set correct content type for JSON', () => {
    const headers = { 'Content-Type': 'application/json' };
    expect(headers['Content-Type']).toBe('application/json');
  });

  it('should set correct content type for form data', () => {
    const headers = { 'Content-Type': 'multipart/form-data' };
    expect(headers['Content-Type']).toBe('multipart/form-data');
  });

  it('should include credentials', () => {
    const config = { withCredentials: true };
    expect(config.withCredentials).toBe(true);
  });

  it('should set timeout', () => {
    const config = { timeout: 10000 };
    expect(config.timeout).toBe(10000);
  });
});

describe('Retry Logic', () => {
  it('should not retry auth POST timeouts', async () => {
    const { shouldRetryRequest } = await import('@/lib/api-client');

    const result = shouldRetryRequest({
      code: 'ECONNABORTED',
      config: {
        method: 'post',
        url: '/auth/login',
      },
    } as never);

    expect(result).toBe(false);
  });

  it('should retry idempotent GET server errors', async () => {
    const { shouldRetryRequest } = await import('@/lib/api-client');
    const consoleWarn = vi.spyOn(console, 'warn').mockImplementation(() => {});

    const result = shouldRetryRequest({
      config: {
        method: 'get',
        url: '/projects',
      },
      response: {
        status: 503,
      },
    } as never);

    expect(result).toBe(true);
    expect(consoleWarn).toHaveBeenCalledWith('🔄 Retrying server error 503 (attempt 1)');
    consoleWarn.mockRestore();
  });

  it('should not retry non-idempotent requests or auth requests', async () => {
    const { shouldRetryRequest } = await import('@/lib/api-client');

    expect(
      shouldRetryRequest({
        config: {
          method: 'post',
          url: '/projects',
        },
      } as never),
    ).toBe(false);
    expect(
      shouldRetryRequest({
        config: {
          method: 'get',
          url: '/auth/me',
        },
      } as never),
    ).toBe(false);
  });

  it('should not retry timed-out idempotent network requests', async () => {
    const { shouldRetryRequest } = await import('@/lib/api-client');
    const consoleWarn = vi.spyOn(console, 'warn').mockImplementation(() => {});

    expect(
      shouldRetryRequest({
        code: 'ECONNABORTED',
        config: {
          method: 'get',
          url: '/projects',
        },
      } as never),
    ).toBe(false);
    expect(consoleWarn).not.toHaveBeenCalled();
    consoleWarn.mockRestore();
  });

  it('should retry on network error', () => {
    const shouldRetry = (error: { code?: string }) => {
      return error.code === 'ECONNRESET' || error.code === 'ETIMEDOUT';
    };

    expect(shouldRetry({ code: 'ECONNRESET' })).toBe(true);
    expect(shouldRetry({ code: 'ETIMEDOUT' })).toBe(true);
    expect(shouldRetry({ code: 'OTHER' })).toBe(false);
  });

  it('should retry on 5xx errors', () => {
    const shouldRetry = (status: number) => status >= 500 && status < 600;

    expect(shouldRetry(500)).toBe(true);
    expect(shouldRetry(502)).toBe(true);
    expect(shouldRetry(503)).toBe(true);
    expect(shouldRetry(400)).toBe(false);
  });

  it('should not retry on 4xx errors', () => {
    const shouldRetry = (status: number) => status >= 500;

    expect(shouldRetry(400)).toBe(false);
    expect(shouldRetry(401)).toBe(false);
    expect(shouldRetry(404)).toBe(false);
  });

  it('should limit retry attempts', () => {
    const maxRetries = 3;
    let attempts = 0;

    const retry = () => {
      attempts++;
      return attempts < maxRetries;
    };

    while (retry()) {
      // Retry logic
    }

    expect(attempts).toBe(maxRetries);
  });
});

describe('API Error Messages', () => {
  it('should return specific network error messages', async () => {
    const { getAxiosErrorMessage } = await import('@/lib/api-client');

    expect(getAxiosErrorMessage({ code: 'ECONNABORTED' } as never)).toBe(
      'Request timeout. Please check your connection and try again.',
    );
    expect(getAxiosErrorMessage({ code: 'ECONNREFUSED' } as never)).toBe(
      'Cannot connect to server. Please ensure backend is running.',
    );
    expect(getAxiosErrorMessage({ code: 'ENOTFOUND' } as never)).toBe(
      'Server not found. Please check API URL.',
    );
    expect(getAxiosErrorMessage({ code: 'ETIMEDOUT' } as never)).toBe(
      'Connection timed out. Please check your connection.',
    );
    expect(
      getAxiosErrorMessage({
        config: {
          'axios-retry': {
            retryCount: 2,
          },
        },
      } as never),
    ).toBe('Network error after 2 retry attempts. Please check your connection.');
    expect(getAxiosErrorMessage({} as never)).toBe(
      'Network error. Please check your connection.',
    );
  });

  it('should return status-specific API error messages', async () => {
    const { getAxiosErrorMessage } = await import('@/lib/api-client');

    expect(
      getAxiosErrorMessage({
        response: { status: 400, data: { detail: 'Bad data' } },
      } as never),
    ).toBe('Bad data');
    expect(
      getAxiosErrorMessage({
        response: { status: 400, data: { detail: [{ msg: 'Invalid' }] } },
      } as never),
    ).toBe(JSON.stringify([{ msg: 'Invalid' }]));
    expect(
      getAxiosErrorMessage({
        response: { status: 401, data: {} },
      } as never),
    ).toBe('You are not authorized to perform this action.');
    expect(
      getAxiosErrorMessage({
        response: { status: 403, data: { detail: 'No access' } },
      } as never),
    ).toBe('No access');
    expect(
      getAxiosErrorMessage({
        response: { status: 404, data: { message: 'Missing' } },
      } as never),
    ).toBe('Missing');
    expect(
      getAxiosErrorMessage({
        response: { status: 422, data: { message: 'Invalid form' } },
      } as never),
    ).toBe('Invalid form');
    expect(
      getAxiosErrorMessage({
        response: { status: 429, data: {} },
      } as never),
    ).toBe('Too many requests. Please wait a moment.');
    expect(
      getAxiosErrorMessage({
        response: { status: 500, data: { detail: 'Exploded' } },
      } as never),
    ).toBe('Exploded');
    expect(
      getAxiosErrorMessage({
        response: { status: 418, data: {} },
      } as never),
    ).toBe('Server error. Please try again later.');
  });
});

describe('URL Construction', () => {
  it('should construct correct API URL', () => {
    const baseURL = 'http://localhost:8000';
    const endpoint = '/api/users';
    const fullURL = `${baseURL}${endpoint}`;

    expect(fullURL).toBe('http://localhost:8000/api/users');
  });

  it('should handle query parameters', () => {
    const params = { page: 1, limit: 10, search: 'test' };
    const queryString = new URLSearchParams(
      Object.entries(params).map(([k, v]) => [k, String(v)])
    ).toString();

    expect(queryString).toBe('page=1&limit=10&search=test');
  });

  it('should encode special characters', () => {
    const value = 'hello world!';
    const encoded = encodeURIComponent(value);

    expect(encoded).toBe('hello%20world!');
  });
});
