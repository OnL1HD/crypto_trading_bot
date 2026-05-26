const rawApiBaseUrl = import.meta.env.VITE_API_BASE_URL

export const API_BASE_URL =
  typeof rawApiBaseUrl === 'string' && rawApiBaseUrl.trim() !== ''
    ? rawApiBaseUrl.replace(/\/+$/, '')
    : 'http://127.0.0.1:8000'

async function readResponseBody(response: Response): Promise<unknown> {
  const contentType = response.headers.get('content-type')

  if (contentType?.includes('application/json')) {
    return response.json()
  }

  return response.text()
}

interface RequestOptions {
  method: string
  signal?: AbortSignal
  body?: unknown
}

async function apiRequest<T>(path: string, options: RequestOptions): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: options.method,
    headers: {
      Accept: 'application/json',
      ...(options.body !== undefined ? { 'Content-Type': 'application/json' } : {}),
    },
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    signal: options.signal,
  })

  const body = await readResponseBody(response)

  if (!response.ok) {
    throw new Error(errorMessageFromBody(body, response.status))
  }

  return body as T
}

function errorMessageFromBody(body: unknown, status: number): string {
  if (typeof body === 'object' && body !== null && 'detail' in body) {
    const detail = body.detail
    if (typeof detail === 'string') {
      return detail
    }
  }

  if (typeof body === 'string' && body.trim() !== '') {
    return body
  }

  return `Request failed with status ${status}`
}

export async function apiGet<T>(path: string, signal?: AbortSignal): Promise<T> {
  return apiRequest<T>(path, { method: 'GET', signal })
}

export async function apiPost<T>(path: string, body?: unknown, signal?: AbortSignal): Promise<T> {
  return apiRequest<T>(path, { method: 'POST', body, signal })
}
