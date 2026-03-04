import type {
  ChatEditResponse,
  ProgressEvent,
  TripRequest,
  TripResponse,
  TripSummary,
} from '@/types';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

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
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  });

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
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, context }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json() as Promise<ChatEditResponse>;
  },

  // ── CRUD ───────────────────────────────────────────────

  listTrips: async (): Promise<TripSummary[]> => {
    const res = await fetch(`${API_BASE}/api/trips`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json() as Promise<TripSummary[]>;
  },

  getTrip: async (id: string): Promise<TripResponse> => {
    const res = await fetch(`${API_BASE}/api/trips/${id}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json() as Promise<TripResponse>;
  },

  deleteTrip: async (id: string): Promise<void> => {
    const res = await fetch(`${API_BASE}/api/trips/${id}`, {
      method: 'DELETE',
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
  },

  // ── Places search ──────────────────────────────────────

  searchPlaces: async (
    query: string,
    lat?: number,
    lng?: number,
  ): Promise<unknown[]> => {
    const params = new URLSearchParams({ query });
    if (lat !== undefined) params.set('lat', String(lat));
    if (lng !== undefined) params.set('lng', String(lng));
    const res = await fetch(`${API_BASE}/api/places/search?${params}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json() as Promise<unknown[]>;
  },

  // ── Tips ───────────────────────────────────────────────

  generateTips: async (
    tripId: string,
    activities: Record<string, unknown>[],
  ): Promise<unknown> => {
    const res = await fetch(`${API_BASE}/api/trips/${tripId}/tips`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(activities),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json() as Promise<unknown>;
  },
};
