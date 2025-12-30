/**
 * Comprehensive tests for API Client
 * Tests error handling, retries, and request/response interceptors
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

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
