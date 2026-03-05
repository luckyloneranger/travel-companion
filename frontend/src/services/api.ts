import type {
  ChatEditResponse,
  Place,
  ProgressEvent,
  TripRequest,
  TripResponse,
  TripSummary,
  User,
} from '@/types';

export interface TipsResponse {
  tips: Record<string, string>;
}

import { AUTH_TOKEN_KEY } from '@/constants';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

/** Return Bearer header if a token is stored (cross-origin / mobile). */
function getAuthHeaders(): Record<string, string> {
  const token = localStorage.getItem(AUTH_TOKEN_KEY);
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/** Handle 401 responses: logout + show sign-in modal. */
async function handle401(res: Response): Promise<void> {
  if (res.status === 401) {
    const { useAuthStore } = await import('@/stores/authStore');
    const { useUIStore } = await import('@/stores/uiStore');
    useAuthStore.getState().logout();
    useUIStore.getState().openSignIn();
    throw new Error('Session expired. Please sign in again.');
  }
}

/**
 * Parse and yield Server-Sent Events from a streaming POST endpoint.
 */
async function* streamSSE(
  url: string,
  body: unknown,
  signal?: AbortSignal,
): AsyncGenerator<ProgressEvent> {
  const response = await fetch(`${API_BASE}${url}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify(body),
    signal,
    credentials: 'include',
  });

  if (response.status === 401) {
    await handle401(response);
  }
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  if (!response.body) throw new Error('No response body');

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const data: unknown = JSON.parse(line.slice(6));
          yield data as ProgressEvent;
        } catch {
          console.warn('Skipping malformed SSE data:', line);
        }
      }
    }
  }
}

export const api = {
  // ── Journey planning ───────────────────────────────────

  planTripStream: (request: TripRequest, signal?: AbortSignal) =>
    streamSSE('/api/trips/plan/stream', request, signal),

  // ── Day plan generation ────────────────────────────────

  generateDayPlansStream: (tripId: string, signal?: AbortSignal) =>
    streamSSE(`/api/trips/${tripId}/days/stream`, {}, signal),

  // ── Chat editing ───────────────────────────────────────

  editTrip: async (
    tripId: string,
    message: string,
    context: string = '',
  ): Promise<ChatEditResponse> => {
    const res = await fetch(`${API_BASE}/api/trips/${tripId}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify({ message, context }),
      credentials: 'include',
    });
    if (res.status === 401) {
      await handle401(res);
    }
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json() as Promise<ChatEditResponse>;
  },

  // ── CRUD ───────────────────────────────────────────────

  listTrips: async (): Promise<TripSummary[]> => {
    const res = await fetch(`${API_BASE}/api/trips`, {
      headers: getAuthHeaders(),
      credentials: 'include',
    });
    if (res.status === 401) {
      await handle401(res);
    }
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json() as Promise<TripSummary[]>;
  },

  getTrip: async (id: string): Promise<TripResponse> => {
    const res = await fetch(`${API_BASE}/api/trips/${id}`, {
      headers: getAuthHeaders(),
      credentials: 'include',
    });
    if (res.status === 401) {
      await handle401(res);
    }
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json() as Promise<TripResponse>;
  },

  deleteTrip: async (id: string): Promise<void> => {
    const res = await fetch(`${API_BASE}/api/trips/${id}`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
      credentials: 'include',
    });
    if (res.status === 401) {
      await handle401(res);
    }
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
  },

  // ── Places search ──────────────────────────────────────

  searchPlaces: async (
    query: string,
    lat?: number,
    lng?: number,
  ): Promise<Place[]> => {
    const params = new URLSearchParams({ query });
    if (lat !== undefined) params.set('lat', String(lat));
    if (lng !== undefined) params.set('lng', String(lng));
    const res = await fetch(`${API_BASE}/api/places/search?${params}`, {
      headers: getAuthHeaders(),
      credentials: 'include',
    });
    if (res.status === 401) {
      await handle401(res);
    }
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json() as Promise<Place[]>;
  },

  // ── Tips ───────────────────────────────────────────────

  generateTips: async (
    tripId: string,
    activities: { place: { place_id: string; name: string }; time_start: string; time_end: string }[],
  ): Promise<TipsResponse> => {
    const res = await fetch(`${API_BASE}/api/trips/${tripId}/tips`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify(activities),
      credentials: 'include',
    });
    if (res.status === 401) {
      await handle401(res);
    }
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json() as Promise<TipsResponse>;
  },

  // ── Auth ─────────────────────────────────────────────────

  getMe: async (): Promise<{ user: User | null }> => {
    const res = await fetch(`${API_BASE}/api/auth/me`, {
      headers: getAuthHeaders(),
      credentials: 'include',
    });
    if (!res.ok) return { user: null };
    return res.json() as Promise<{ user: User | null }>;
  },

  logout: async (): Promise<void> => {
    await fetch(`${API_BASE}/api/auth/logout`, {
      method: 'POST',
      headers: getAuthHeaders(),
      credentials: 'include',
    });
  },

  // ── Sharing ──────────────────────────────────────────────

  shareTrip: async (tripId: string): Promise<{ token: string; url: string }> => {
    const res = await fetch(`${API_BASE}/api/trips/${tripId}/share`, {
      method: 'POST',
      headers: getAuthHeaders(),
      credentials: 'include',
    });
    if (res.status === 401) {
      await handle401(res);
    }
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json() as Promise<{ token: string; url: string }>;
  },

  getSharedTrip: async (token: string): Promise<TripResponse> => {
    const res = await fetch(`${API_BASE}/api/shared/${token}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json() as Promise<TripResponse>;
  },

  // ── Export ───────────────────────────────────────────────

  exportPdf: async (tripId: string): Promise<void> => {
    const res = await fetch(`${API_BASE}/api/trips/${tripId}/export/pdf`, {
      headers: getAuthHeaders(),
      credentials: 'include',
    });
    if (res.status === 401) {
      await handle401(res);
    }
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `trip-${tripId}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  },

  exportCalendar: async (tripId: string): Promise<void> => {
    const res = await fetch(`${API_BASE}/api/trips/${tripId}/export/calendar`, {
      headers: getAuthHeaders(),
      credentials: 'include',
    });
    if (res.status === 401) {
      await handle401(res);
    }
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `trip-${tripId}.ics`;
    a.click();
    URL.revokeObjectURL(url);
  },
};
