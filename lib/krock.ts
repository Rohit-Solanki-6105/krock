/**
 * Krock Framework Client Utilities
 */

export interface KrockFetchOptions extends RequestInit {
  params?: Record<string, any>;
}

/**
 * Universal client fetch helper for Krock API endpoints
 */
export async function krockFetch<T = any>(
  url: string,
  options: KrockFetchOptions = {}
): Promise<T> {
  const { params, headers, ...restOptions } = options;

  let requestUrl = url;
  if (params && Object.keys(params).length > 0) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, val]) => {
      if (val !== undefined && val !== null) {
        searchParams.append(key, String(val));
      }
    });
    requestUrl += (requestUrl.includes('?') ? '&' : '?') + searchParams.toString();
  }

  const response = await fetch(requestUrl, {
    headers: {
      'Content-Type': 'application/json',
      ...headers,
    },
    ...restOptions,
  });

  if (!response.ok) {
    const errorBody = await response.text();
    let errorMessage = `HTTP Error ${response.status}: ${response.statusText}`;
    try {
      const parsed = JSON.parse(errorBody);
      if (parsed.error) errorMessage = parsed.error;
    } catch (_) {}
    throw new Error(errorMessage);
  }

  return response.json() as Promise<T>;
}

/**
 * Extract window parameters injected by Krock SSR
 */
export function getKrockParams<T = Record<string, string>>(): T {
  if (typeof window !== 'undefined' && (window as any).__PARAMS__) {
    return (window as any).__PARAMS__ as T;
  }
  return {} as T;
}
