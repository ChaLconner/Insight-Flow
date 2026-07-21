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
  waitForBackend,
  getAxiosErrorMessage,
  downloadFile,
  isAxiosError,
  ApiError,
} from '@/lib/api-client';

describe('API Client Configuration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.restoreAllMocks();
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

  it('should handle POST, PUT, PATCH, DELETE requests with data and query params', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation(async () => {
      return new Response(JSON.stringify({ ok: true }), {
        status: 200,
        statusText: 'OK',
        headers: { 'Content-Type': 'application/json' },
      });
    });

    await apiClient.post('/test-post', { a: 1 }, { params: { query: 'search', page: 2 } });
    await apiClient.put('/test-put', { b: 2 });
    await apiClient.patch('/test-patch', { c: 3 });
    await apiClient.delete('/test-delete');

    expect(fetchSpy).toHaveBeenCalledTimes(4);
  });

  it('should handle FormData body in POST request', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify({ uploaded: true }), { status: 200 })
    );

    const fd = new FormData();
    fd.append('file', new Blob(['test']));

    await apiClient.post('/upload', fd);
    expect(fetchSpy).toHaveBeenCalled();
  });

  it('should handle text and blob responseTypes', async () => {
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response('plain text response', { status: 200 }))
      .mockResolvedValueOnce(new Response(new Blob(['blob content']), { status: 200 }));

    const textRes = await apiClient.get('/text-endpoint', { responseType: 'text' });
    expect(textRes.data).toBe('plain text response');

    const blobRes = await apiClient.get('/blob-endpoint', { responseType: 'blob' });
    expect(blobRes.data).toBeInstanceOf(Blob);
  });

  it('should handle non-JSON text responses gracefully', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response('raw text content', { status: 200 })
    );

    const res = await apiClient.get('/raw');
    expect(res.data).toBe('raw text content');
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

  it('should handle network abort / timeout error', async () => {
    const abortErr = new Error('The operation was aborted');
    abortErr.name = 'AbortError';
    vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(abortErr);

    await expect(apiClient.get('/timeout')).rejects.toThrow('Request timeout. Please try again.');
  });

  it('should identify ApiError with isAxiosError helper for backward compatibility', () => {
    const err = new ApiError('Test error', {
      data: {},
      status: 400,
      statusText: 'Bad Request',
      headers: {},
    });
    expect(isAxiosError(err)).toBe(true);
    expect(isAxiosError(null)).toBe(false);
    expect(isAxiosError({})).toBe(false);
  });

  it('should create form data from mixed values and nested arrays/objects', () => {
    const file = new File(['hello'], 'hello.txt', { type: 'text/plain' });
    const formData = createFormData({
      title: 'Report',
      count: 2,
      active: true,
      file,
      tags: ['alpha', 'beta'],
      items: [{ id: 1 }, { id: 2 }],
      meta: { owner: 'qa' },
      empty: null,
      undef: undefined,
    });

    expect(formData.get('title')).toBe('Report');
    expect(formData.get('count')).toBe('2');
    expect(formData.get('active')).toBe('true');
    expect(formData.get('file')).toBe(file);
    expect(formData.get('tags[0]')).toBe('alpha');
    expect(formData.get('tags[1]')).toBe('beta');
    expect(formData.get('items[0][id]')).toBe('1');
    expect(formData.get('meta')).toBe(JSON.stringify({ owner: 'qa' }));
    expect(formData.has('empty')).toBe(false);
    expect(formData.has('undef')).toBe(false);
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

  it('should create custom API clients', async () => {
    const client = createCustomApiClient('http://api.test', 2500);
    expect(client).toBeDefined();
    expect(typeof client.get).toBe('function');
    expect(typeof client.post).toBe('function');

    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify({ ok: true }), { status: 200 })
    );
    const res = await client.get('/items');
    expect(res.status).toBe(200);
  });

  it('should report backend health status', async () => {
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ status: 'healthy' }), {
          status: 200,
          statusText: 'OK',
        })
      )
      .mockRejectedValueOnce(new Error('Down'));

    expect(await checkBackendHealth()).toBe(true);
    expect(await checkBackendHealth()).toBe(false);
  });

  it('should wait for backend health check', async () => {
    vi.spyOn(globalThis, 'fetch')
      .mockRejectedValueOnce(new Error('Down'))
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ status: 'healthy' }), { status: 200 })
      );

    const ready = await waitForBackend(3, 10);
    expect(ready).toBe(true);

    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('Down'));
    const failed = await waitForBackend(2, 10);
    expect(failed).toBe(false);
  });
});

describe('getAxiosErrorMessage helper', () => {
  it('should handle network errors without response', () => {
    expect(getAxiosErrorMessage({ code: 'ECONNABORTED' })).toBe(
      'Request timeout. Please check your connection and try again.'
    );
    expect(getAxiosErrorMessage({ code: 'UNKNOWN' })).toBe(
      'Network error. Please check your connection.'
    );
  });

  it('should handle status codes correctly', () => {
    expect(getAxiosErrorMessage({ response: { status: 400, data: { message: 'Bad request' } } })).toBe('Bad request');
    expect(getAxiosErrorMessage({ response: { status: 400, data: { detail: 'String detail' } } })).toBe('String detail');
    expect(getAxiosErrorMessage({ response: { status: 400, data: { detail: { msg: 'err' } } } })).toBe(JSON.stringify({ msg: 'err' }));
    expect(getAxiosErrorMessage({ response: { status: 400, data: {} } })).toBe('Please check your input and try again.');

    expect(getAxiosErrorMessage({ response: { status: 401, data: {} } })).toBe('You are not authorized to perform this action.');
    
    expect(getAxiosErrorMessage({ response: { status: 403, data: { message: 'Forbidden' } } })).toBe('Forbidden');
    expect(getAxiosErrorMessage({ response: { status: 403, data: { detail: 'Detail forbidden' } } })).toBe('Detail forbidden');
    expect(getAxiosErrorMessage({ response: { status: 403, data: {} } })).toBe('Access denied.');

    expect(getAxiosErrorMessage({ response: { status: 404, data: { message: 'Not found msg' } } })).toBe('Not found msg');
    expect(getAxiosErrorMessage({ response: { status: 404, data: { detail: 'Not found detail' } } })).toBe('Not found detail');
    expect(getAxiosErrorMessage({ response: { status: 404, data: {} } })).toBe('The requested resource was not found.');

    expect(getAxiosErrorMessage({ response: { status: 422, data: { message: 'Unprocessable' } } })).toBe('Unprocessable');
    expect(getAxiosErrorMessage({ response: { status: 429, data: {} } })).toBe('Too many requests. Please wait a moment.');

    expect(getAxiosErrorMessage({ response: { status: 500, data: { message: 'Server error msg' } } })).toBe('Server error msg');
    expect(getAxiosErrorMessage({ response: { status: 500, data: { detail: 'Server detail' } } })).toBe('Server detail');
    expect(getAxiosErrorMessage({ response: { status: 500, data: {} } })).toBe('Server error. Please try again later.');

    expect(getAxiosErrorMessage({ response: { status: 503, data: {} } })).toBe('Server error. Please try again later.');
  });
});

describe('downloadFile helper', () => {
  it('should trigger file download using Blob', async () => {
    const dummyBlob = new Blob(['hello']);
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(dummyBlob, { status: 200 })
    );

    const createObjectURLMock = vi.fn().mockReturnValue('blob:http://localhost/123');
    const revokeObjectURLMock = vi.fn();
    window.URL.createObjectURL = createObjectURLMock;
    window.URL.revokeObjectURL = revokeObjectURLMock;

    const linkClickSpy = vi.fn();
    const anchorMock = {
      href: '',
      download: '',
      click: linkClickSpy,
    } as unknown as HTMLAnchorElement;

    vi.spyOn(document, 'createElement').mockReturnValue(anchorMock);
    vi.spyOn(document.body, 'appendChild').mockImplementation(() => anchorMock);
    vi.spyOn(document.body, 'removeChild').mockImplementation(() => anchorMock);

    await downloadFile('/file/download', 'my-file.pdf');

    expect(createObjectURLMock).toHaveBeenCalled();
    expect(linkClickSpy).toHaveBeenCalled();
    expect(revokeObjectURLMock).toHaveBeenCalledWith('blob:http://localhost/123');
  });

  it('should throw error when download fails', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new Error('Network error'));
    await expect(downloadFile('/fail')).rejects.toThrow('Network error');
  });
});
