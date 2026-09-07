export const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export function getAuthToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('access_token');
}

export function setAuthToken(token: string) {
  if (typeof window !== 'undefined') {
    localStorage.setItem('access_token', token);
  }
}

export function clearAuthToken() {
  if (typeof window !== 'undefined') {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user_info');
  }
}

export function getUserInfo() {
  if (typeof window === 'undefined') return null;
  const raw = localStorage.getItem('user_info');
  return raw ? JSON.parse(raw) : null;
}

export async function fetchWithAuth(endpoint: string, options: RequestInit = {}) {
  const token = getAuthToken();
  const isFormData = options.body instanceof FormData;
  const headers = {
    ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
    });

    if (response.status === 401) {
      clearAuthToken();
      if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
        window.location.href = '/login';
      }
    }

    return response;
  } catch (err: any) {
    console.warn(`API call to ${endpoint} failed:`, err);
    return new Response(
      JSON.stringify({ detail: 'Backend server is unreachable. Please ensure FastAPI backend is running on port 8000.' }),
      { status: 503, headers: { 'Content-Type': 'application/json' } }
    );
  }
}
