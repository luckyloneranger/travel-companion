// Minimal API service stub — will be replaced with full implementation.

import type { TripSummary, TripResponse } from '@/types';

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  listTrips: () => request<TripSummary[]>('/api/trips'),

  getTrip: (id: string) => request<TripResponse>(`/api/trips/${id}`),

  deleteTrip: (id: string) =>
    request<void>(`/api/trips/${id}`, { method: 'DELETE' }),
};
